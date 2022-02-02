"""
from sqlalchemy import (
        Column, Integer, String, Boolean, ForeignKey, Table, TIMESTAMP,
        LargeBinary
        )
"""
#from sqlalchemy import create_engine
#from sqlalchemy.orm import relationship, backref
#from flask_login import UserMixin
#import datetime

from app import db

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    prompt = db.Column(db.String, nullable=False)
    answer = db.Column(db.String, nullable=False)

    def __repr__(self):
        return f"<Question {self.prompt}>"
