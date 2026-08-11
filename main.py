from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_debugtoolbar import DebugToolbarExtension
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf import CSRFProtect
from forms import LoginForm, RegisterForm, EmptyForm
from extensions import db
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

app = Flask(__name__)
app.debug = True
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SECRET_KEY'] = 'sekretnyklucz'
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False

csrf = CSRFProtect(app)
toolbar = DebugToolbarExtension(app)
# initialize shared db with app
db.init_app(app)

# Tworzy bazy danych na startup
with app.app_context():
    import player
    db.create_all()

# Initialize APScheduler
scheduler = BackgroundScheduler()

def increment_all_scores():
    """Increment score for all players based on their workers"""
    with app.app_context():
        from player import Player
        players = Player.query.filter(Player.camp != None).all()
        for player in players:
            player.score = player.score + 1 + player.workers
        db.session.commit()

# Schedule the task to run every second
scheduler.add_job(func=increment_all_scores, trigger="interval", seconds=1)
scheduler.start()

# Shut down the scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown())

# Import models
from player import User, Player

# Strona główna
@app.route('/', methods=['GET'])
def home():
    form = LoginForm()
    increment_form = EmptyForm()
    if session.get('user_id'):
        return redirect(url_for('dashboard'))
    return render_template('index.html', form=form, increment_form=increment_form)

# Dashboard
@app.route('/dashboard', methods=['GET'])
def dashboard():
    if not session.get('user_id'):
        return redirect(url_for('home'))
    
    user = User.query.filter_by(id=session.get('user_id')).first()
    player = Player.query.filter_by(user_id=session.get('user_id')).first()
    if player is None:
        # create player record if missing
        player = Player(user_id=session.get('user_id'))
        db.session.add(player)
        db.session.commit()
    
    if player.camp is None:
        return redirect(url_for('choose_camp'))
    
    increment_form = EmptyForm()
    user_score = player.score
    username = user.username if user else 'Unknown'
    
    camp_names = {'stary': 'Kopacza', 'nowy': 'Kreta', 'bagno': 'Nowicjusza'}
    camp_plural = {'stary': 'Kopacze', 'nowy': 'Krety', 'bagno': 'Nowicjusze'}
    camp_costs = {'stary': 99999, 'nowy': 999999, 'bagno': 9999999}
    worker_name = camp_names.get(player.camp, 'pracownik')
    workers_plural = camp_plural.get(player.camp, 'Pracownicy')
    build_cost = camp_costs.get(player.camp, 999999)
    
    return render_template('dashboard.html', increment_form=increment_form, user_score=user_score, username=username, workers=player.workers, worker_cost=2137, camp=player.camp, worker_name=worker_name, workers_plural=workers_plural, camp_built=player.camp_built, build_cost=build_cost)

# Buy worker
@app.route('/buy_worker', methods=['POST'])
def buy_worker():
    if not session.get('user_id'):
        return {'error': 'Not logged in'}, 403
    
    from player import Player
    player = Player.query.filter_by(user_id=session.get('user_id')).first()
    
    if player is None or player.score < 2137:
        return {'error': 'Not enough score'}, 400
    
    player.score -= 2137
    player.workers += 1
    db.session.commit()
    
    return {'score': player.score, 'workers': player.workers}, 200

# Build camp
@app.route('/build_camp', methods=['POST'])
def build_camp():
    if not session.get('user_id'):
        return {'error': 'Not logged in'}, 403
    
    from player import Player
    player = Player.query.filter_by(user_id=session.get('user_id')).first()
    
    camp_costs = {'stary': 99999, 'nowy': 999999, 'bagno': 9999999}
    cost = camp_costs.get(player.camp, 999999)
    
    if player is None or player.score < cost:
        return {'error': 'Not enough score'}, 400
    
    if player.camp_built:
        return {'error': 'Camp already built'}, 400
    
    player.score -= cost
    player.camp_built = True
    db.session.commit()
    
    return {'score': player.score, 'camp_built': True}, 200

# Logowanie
@app.route('/login', methods=['POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            from player import Player
            player = Player.query.filter_by(user_id=user.id).first()
            if player is None:
                player = Player(user_id=user.id, score=0)
                db.session.add(player)
            db.session.commit()
            
            session['user_id'] = user.id
            return redirect(url_for('dashboard'))
        return redirect(url_for('home'))

# Wybór obozu
@app.route('/choose_camp', methods=['GET', 'POST'])
def choose_camp():
    if not session.get('user_id'):
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        camp = request.form.get('camp')
        if camp in ['stary', 'nowy', 'bagno']:
            from player import Player
            player = Player.query.filter_by(user_id=session.get('user_id')).first()
            if player:
                player.camp = camp
                db.session.commit()
                return redirect(url_for('dashboard'))
    
    return render_template('choose_camp.html')

# Rejestracja użytkownika
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        new_user = User(username=username, password=generate_password_hash(password))
        db.session.add(new_user)
        db.session.commit()
        # create player record for new user
        from player import Player
        player = Player(user_id=new_user.id)
        db.session.add(player)
        db.session.commit()
        return redirect(url_for('home'))
    return render_template('register.html', form=form)

# Wyloguj
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('home'))

# Cheat endpoint
@app.route('/bmarvinb', methods=['GET'])
def cheat():
    if not session.get('user_id'):
        return 'Not logged in', 403
    
    from player import Player
    player = Player.query.filter_by(user_id=session.get('user_id')).first()
    if player:
        player.score += 999999
        db.session.commit()
        return f'Added 999999 score! Total: {player.score}', 200
    return 'Player not found', 404

# Increment score
@app.route('/increment_score', methods=['POST'])
def increment_score():
    # CSRF protection for POST requests
    token = request.headers.get('X-CSRFToken') or request.form.get('csrf_token')
    if not token:
        return '', 403  # Forbidden
    
    from flask_wtf.csrf import validate_csrf
    try:
        validate_csrf(token)
    except:
        return '', 403  # Forbidden
    
    if session.get('user_id'):
        # Logged in user - save to database
        from player import Player
        player = Player.query.filter_by(user_id=session.get('user_id')).first()
        if player is None:
            player = Player(user_id=session.get('user_id'), score=1)
            db.session.add(player)
        else:
            player.score = player.score + 1
        db.session.commit()
    else:
        # Logged out user - save to session
        session['guest_score'] = session.get('guest_score', 0) + 1
        session.modified = True  # Ensure session is saved
    
    return '', 204  # Return empty response with 204 No Content

# Debug (kept)
@app.route('/debug', methods=['GET', 'POST'])
def debug():
    import pdb; pdb.set_trace()

if __name__ == '__main__':
    app.run(debug=True)
