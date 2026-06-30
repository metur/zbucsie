from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length

class LoginForm(FlaskForm):
    username = StringField('Nazwa użytkownika', validators=[DataRequired(), Length(max=80)])
    password = PasswordField('Hasło', validators=[DataRequired()])
    submit = SubmitField('Zaloguj')

class RegisterForm(FlaskForm):
    username = StringField('Nazwa użytkownika', validators=[DataRequired(), Length(max=80)])
    password = PasswordField('Hasło', validators=[DataRequired()])
    submit = SubmitField('Zarejestruj')
