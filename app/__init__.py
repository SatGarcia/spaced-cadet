import os
import logging, logging.handlers

from flask import Flask
from flask_sqlalchemy import SQLAlchemy


#import rq
#from redis import Redis

#from . import db
#from . import admin
#from . import user_views

db = SQLAlchemy()


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)

    app.config.from_object('config')
    app.config.from_pyfile('config.py', silent=True)

    # setting of logging of app-specific messages to cadet.log
    handler = logging.FileHandler('cadet.log')
    handler.setLevel(app.config.get('LOGGING_LEVEL', logging.INFO))
    formatter = logging.Formatter('%(asctime)s %(levelname)s [%(filename)s:%(lineno)d - %(funcName)s] : %(message)s')
    handler.setFormatter(formatter)
    app.logger.addHandler(handler)

    if app.config.get('EMAIL_ERRORS', False):
        # email error and critical events to admin(s)
        mail_handler = logging.handlers.SMTPHandler(mailhost=app.config['SMTP_SERVER'],
                                                    fromaddr=app.config['EMAIL_FROM'],
                                                    toaddrs=app.config['EMAIL_ERRORS_TO'],
                                                    subject="SpacedCadet Error Report")
        mail_handler.setLevel(logging.ERROR)
        app.logger.addHandler(mail_handler)

    # ensure that the instance folder exists (creating if necessary)
    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)

    with app.app_context():
        db.drop_all() # clear out table (testing only FIXME)
        db.create_all()

        # set up some example entries in the database for testing
        section = db_models.Section(course="COMP110", number=3)
        db.session.add(section)
        student = db_models.Student(username="sat", email="sat@sandeigeo.edu",
                                    first_name="Sat", last_name="Garcia")
        db.session.add(student)
        section.students.append(student)
        db.session.commit()

        """
        source = db_models.Source(description="Textbook Section 3.5")
        db.session.add(source)
        section.sources.append(source)

        assessment = db_models.Assessment(description="Quiz 1")
        db.session.add(assessment)
        section.assessments.append(assessment)
        """

        lo = db_models.Objective(description="Use basic programming terminology")
        db.session.add(lo)
        #source.objectives.append(lo)
        #assessment.objectives.append(lo)
        db.session.commit()

        q1 = db_models.Question(prompt="vegan", answer="A cool person")
        q2 = db_models.Question(prompt="cat", answer="Cute furrball")
        q3 = db_models.Question(prompt="olives", answer="Nasty stuff")
        db.session.add(q1)
        db.session.add(q2)
        db.session.add(q3)
        lo.questions.append(q1)
        lo.questions.append(q2)
        lo.questions.append(q3)
        section.questions.append(q1)
        section.questions.append(q2)
        section.questions.append(q3)
        db.session.commit()

        for q in db_models.Question.query:
            print(repr(q))


    from app.user_views import user_views as uv
    app.register_blueprint(uv)

    return app

from app import db_models
