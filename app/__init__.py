import os
import logging, logging.handlers

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

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
        user = db_models.User(email="sat@sandiego.edu",
                              first_name="Sat", last_name="Garcia",
                              admin=True, instructor=True)
        user.set_password("foobar")
        db.session.add(user)
        section.users.append(user)
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

        q1 = db_models.ShortAnswerQuestion(prompt="Define: **vegan**",
                                answer="A _cool_ person")
        q2 = db_models.AutoCheckQuestion(prompt="What number is the result of the following computation: $2^3-1$",
                                answer="7")

        q3 = db_models.MultipleChoiceQuestion(prompt="Why is **less** code better?")
        o1 = db_models.AnswerOption(text="Fewer lines to have bugs in.",
                                    correct=True)
        o2 = db_models.AnswerOption(text="Because Dr. Sat said so.")
        o3 = db_models.AnswerOption(text="Allows more laziness.")

        q4 = db_models.CodeJumbleQuestion(prompt="Write a `for` loop that prints the numbers from 1 to 10.",
                                          language="python")
        b1 = db_models.JumbleBlock(code="# display a value\nprint(i)", correct_index=1, correct_indent=1)
        b2 = db_models.JumbleBlock(code="x = 5", correct_index=-1, correct_indent=0)
        b3 = db_models.JumbleBlock(code="for i in range(1, 11):", correct_index=0, correct_indent=0)

        q5 = db_models.ShortAnswerQuestion(prompt=\
"""
Describe what line 2 does in the following code.

```python
x = 7
y = x
```
""",
                                           answer="It creates a new variable that refers to the same value as x.")

        db.session.add(q1)
        db.session.add(q2)
        db.session.add(q3)
        db.session.add(q4)
        db.session.add(q5)
        q3.options.append(o1)
        q3.options.append(o2)
        q3.options.append(o3)
        q4.blocks.append(b1)
        q4.blocks.append(b2)
        q4.blocks.append(b3)
        lo.questions.append(q1)
        lo.questions.append(q2)
        lo.questions.append(q3)
        lo.questions.append(q4)
        lo.questions.append(q5)
        section.questions.append(q1)
        section.questions.append(q2)
        section.questions.append(q3)
        section.questions.append(q4)
        section.questions.append(q5)
        db.session.commit()

        for q in db_models.Question.query:
            print(repr(q))

    from app.user_views import user_views as uv
    app.register_blueprint(uv)

    from app.api import init_app as init_api
    init_api(app)

    from app.auth import auth
    app.register_blueprint(auth, url_prefix="/auth")

    from app.auth import init_app as init_auth
    init_auth(app)


    return app

from app import db_models
