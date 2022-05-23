import os
import logging, logging.handlers

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from flask_jsglue import JSGlue

from elasticsearch import Elasticsearch

db = SQLAlchemy()
mail = Mail()
jsglue = JSGlue()

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

    mail.init_app(app)
    jsglue.init_app(app)

    app.elasticsearch = Elasticsearch([app.config['ELASTICSEARCH_URL']]) \
        if app.config['ELASTICSEARCH_URL'] else None

    from app.database import init_app as init_db
    init_db(app)

    from app.user_views import user_views as uv
    app.register_blueprint(uv)

    from app.user_views import markdown_to_html
    app.jinja_env.filters['mdown'] = markdown_to_html

    from app.api import init_app as init_api
    init_api(app)

    from app.instructor import instructor
    app.register_blueprint(instructor)

    from app.auth import auth
    app.register_blueprint(auth, url_prefix="/auth")

    from app.auth import init_app as init_auth
    init_auth(app)


    return app

from app import db_models
