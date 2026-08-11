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

# Initialize APScheduler
scheduler = BackgroundScheduler()

def increment_all_scores():
    """Increment score for all players based on their workers"""
    with app.app_context():
        from player import Player
        players = Player.query.filter_by(first_login=True).all()
        for player in players:
            player.score = player.score + 1 + player.workers
        db.session.commit()

# Schedule the task to run every second
scheduler.add_job(func=increment_all_scores, trigger="interval", seconds=1)
scheduler.start()

# Shut down the scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown())

# Model użytkownika
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)

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
        flash('Musisz być zalogowany')
        return redirect(url_for('home'))
    
    user = User.query.filter_by(id=session.get('user_id')).first()
    from player import Player
    player = Player.query.filter_by(user_id=session.get('user_id')).first()
    if player is None:
        # create player record if missing
        player = Player(user_id=session.get('user_id'))
        db.session.add(player)
        db.session.commit()
    
    increment_form = EmptyForm()
    user_score = player.score
    username = user.username if user else 'Unknown'
    return render_template('dashboard.html', increment_form=increment_form, user_score=user_score, username=username, workers=player.workers, worker_cost=21)

# Buy worker
@app.route('/buy_worker', methods=['POST'])
def buy_worker():
    if not session.get('user_id'):
        return {'error': 'Not logged in'}, 403
    
    from player import Player
    player = Player.query.filter_by(user_id=session.get('user_id')).first()
    
    if player is None or player.score < 21:
        return {'error': 'Not enough score'}, 400
    
    player.score -= 21
    player.workers += 1
    db.session.commit()
    
    return {'score': player.score, 'workers': player.workers}, 200

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
                player = Player(user_id=user.id, score=0, first_login=True)
                db.session.add(player)
            else:
                player.first_login = True
            db.session.commit()
            
            session['user_id'] = user.id
            flash(f"Witaj, {user.username}!")
            return redirect(url_for('dashboard'))
        flash("Nieprawidłowa nazwa użytkownika lub hasło!")
    else:
        flash('Błąd formularza')
    return redirect(url_for('home'))

# Rejestracja użytkownika
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        if User.query.filter_by(username=username).first():
            flash("Użytkownik już istnieje!")
            return redirect(url_for('home'))
        new_user = User(username=username, password=generate_password_hash(password))
        db.session.add(new_user)
        db.session.commit()
        # create player record for new user
        from player import Player
        player = Player(user_id=new_user.id)
        db.session.add(player)
        db.session.commit()
        flash("Zarejestrowano pomyślnie. Możesz się zalogować.")
        return redirect(url_for('home'))
    return render_template('register.html', form=form)

# Wyloguj
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash("Wylogowano")
    return redirect(url_for('home'))

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
    with app.app_context():
        # Ensure models are imported so SQLAlchemy knows about all tables
        import player
        db.create_all()  # Tworzenie tabeli w bazie danych
    app.run(debug=True)
