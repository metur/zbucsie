from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_debugtoolbar import DebugToolbarExtension
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf import CSRFProtect
from forms import LoginForm, RegisterForm, EmptyForm
from extensions import db

app = Flask(__name__)
app.debug = True
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SECRET_KEY'] = 'sekretnyklucz'
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False

csrf = CSRFProtect(app)
toolbar = DebugToolbarExtension(app)
# initialize shared db with app
db.init_app(app)

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
    user_score = None
    if session.get('user_id'):
        # late import to avoid circular import
        from player import Player
        player = Player.query.filter_by(user_id=session.get('user_id')).first()
        if player is None:
            # create player record if missing
            player = Player(user_id=session.get('user_id'))
            db.session.add(player)
            db.session.commit()
        user_score = player.score
    return render_template('index.html', form=form, increment_form=increment_form, user_score=user_score)

# Logowanie
@app.route('/login', methods=['POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            flash(f"Witaj, {user.username}!")
            return redirect(url_for('home'))
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
    form = EmptyForm()
    if not form.validate_on_submit():
        flash('Invalid request (CSRF token missing or invalid)')
        return redirect(url_for('home'))
    if not session.get('user_id'):
        flash('Musisz być zalogowany')
        return redirect(url_for('home'))
    from player import Player
    player = Player.query.filter_by(user_id=session.get('user_id')).first()
    if player is None:
        player = Player(user_id=session.get('user_id'), score=1)
        db.session.add(player)
    else:
        player.score = player.score + 1
    db.session.commit()
    flash('Score increased')
    return redirect(url_for('home'))

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
