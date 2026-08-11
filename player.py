from extensions import db

# Model gracza
class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    score = db.Column(db.Integer, default=0)
    workers = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=db.func.now())
    first_login = db.Column(db.Boolean, default=False)

    user = db.relationship('User', backref=db.backref('player', uselist=False))