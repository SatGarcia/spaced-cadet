#from flask_login import UserMixin
from datetime import datetime

from app import db

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    prompt = db.Column(db.String, nullable=False)
    answer = db.Column(db.String, nullable=False)

    # entries for SM-2 Algorithm
    next_attempt = db.Column(db.Date, default=datetime.today, nullable=False)
    e_factor = db.Column(db.Float, default=2.5, nullable=False)
    interval = db.Column(db.Integer, default=1, nullable=False)

    attempts = db.relationship('Attempt', backref='question', lazy='dynamic')

    def __repr__(self):
        return f"<Question {self.id}: {self.prompt}>"

class Attempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    time = db.Column(db.DateTime, default=datetime.utcnow)
    response = db.Column(db.String, nullable=False)
    correct = db.Column(db.Boolean)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'))

    def __repr__(self):
        return f"<Attempt {self.id}: Question {self.question.id} at {self.time}>"
