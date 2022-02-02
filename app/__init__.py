import os
import logging, logging.handlers

from flask import Flask
from sqlalchemy.orm import sessionmaker

#import rq
#from redis import Redis

from . import db
#from . import admin


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

    db_engine = db.init_db(app)
    app.Session = sessionmaker(db_engine)

    #app.register_blueprint(admin.admin, url_prefix="/admin")
    #app.register_blueprint(user_views.user_views)

    db.init_app(app)

    return app
