#from flask_login import UserMixin
from datetime import datetime

from app import db

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    prompt = db.Column(db.String, nullable=False)
    answer = db.Column(db.String, nullable=False)
    attempts = db.relationship('Attempt', backref='question', lazy='dynamic')

    def __repr__(self):
        return f"<Question {self.prompt}>"

class Attempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    time = db.Column(db.DateTime, default=datetime.utcnow)
    response = db.Column(db.String, nullable=False)
    correct = db.Column(db.Boolean)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'))

    def __repr__(self):
        return f"<Attempt {self.id}: Question {self.question.id} at {self.time}>"
