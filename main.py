from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_debugtoolbar import DebugToolbarExtension

app = Flask(__name__)
app.debug = True
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SECRET_KEY'] = 'sekretnyklucz'
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
toolbar = DebugToolbarExtension(app)
db = SQLAlchemy(app)

# Model użytkownika
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)

# Strona główna
@app.route('/', methods=['GET'])
def home():
    return render_template('index.html')

# Logowanie
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            session['user_id'] = user.id
            flash(f"Witaj, {user.username}!")
            return redirect(url_for('home'))
        flash("Nieprawidłowa nazwa użytkownika lub hasło!")
        return redirect(url_for('home'))
    return redirect(url_for('home'))

# Rejestracja użytkownika
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            flash("Użytkownik już istnieje!")
            return redirect(url_for('home'))
        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()
        flash("Zarejestrowano pomyślnie. Możesz się zalogować.")
        return redirect(url_for('home'))
    return render_template('register.html')

# Wyloguj
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash("Wylogowano")
    return redirect(url_for('home'))

# Debug (kept)
@app.route('/debug', methods=['GET', 'POST'])
def debug():
    import pdb;
    pdb.set_trace()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Tworzenie tabeli w bazie danych
    app.run(debug=True)
