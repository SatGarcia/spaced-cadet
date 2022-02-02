from sqlalchemy import (
        Column, Integer, String, Boolean, ForeignKey, Table, TIMESTAMP,
        LargeBinary
        )
from sqlalchemy import create_engine
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import declarative_base
#from flask_login import UserMixin
import datetime

Base = declarative_base()


class Question(Base):
    __tablename__ = "question"
    id = Column(Integer, primary_key=True)
    prompt = Column(String, nullable=False)
    answer = Column(String, nullable=False)

    # many-to-many relationship
    """
    learning_objectives = relationship(
        "LearningObjective", secondary=objective_pairing,
        order_by="User.last_name", back_populates="questions"
    )
    """
