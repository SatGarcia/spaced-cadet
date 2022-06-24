import os
import logging, logging.handlers

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_mail import Mail
from flask_jsglue import JSGlue

from elasticsearch import Elasticsearch

db = SQLAlchemy()
migrate = Migrate()
mail = Mail()
jsglue = JSGlue()

def create_app(config_class='config.DevelopmentConfig'):
    app = Flask(__name__, instance_relative_config=True)

    # load the configuration from the specified configuration class, then from
    # the instance/config.py file, which will override anything in
    # config_class
    app.config.from_object(config_class)
    app.config.from_pyfile('config.py', silent=True)

    # setting of logging of app-specific messages to cadet.log
    handler = logging.FileHandler('cadet.log')
    handler.setLevel(app.config.get('LOGGING_LEVEL', logging.INFO))
    formatter = logging.Formatter('%(asctime)s %(levelname)s [%(filename)s:%(lineno)d - %(funcName)s] : %(message)s')
    handler.setFormatter(formatter)
    app.logger.addHandler(handler)

    if app.config.get('EMAIL_ERRORS', False):
        # email error and critical events to admin(s)
        mail_handler = logging.handlers.SMTPHandler(mailhost=app.config['MAIL_SERVER'],
                                                    fromaddr=app.config['EMAIL_FROM'],
                                                    toaddrs=app.config['EMAIL_ERRORS_TO'],
                                                    subject="SpacedCadet Error Report")
        mail_handler.setLevel(logging.ERROR)
        app.logger.addHandler(mail_handler)

    # ensure that the instance folder exists (creating if necessary)
    os.makedirs(app.instance_path, exist_ok=True)

    mail.init_app(app)
    jsglue.init_app(app)

    es_url = app.config.get('ELASTICSEARCH_URL')
    if es_url:
        app.elasticsearch = Elasticsearch(es_url)

        # check that elasticsearch server is actually available
        if not app.elasticsearch.ping():
            app.logger.warn("Could not connect to Elasticsearch server.")
            app.elasticsearch = None

    else:
        app.elasticsearch = None


    from app.database import init_app as init_db
    init_db(app)

    migrate.init_app(app, db)

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

    if app.config.get('ENABLE_TEST_ROUTES'):
        from app.tests import tests
        app.register_blueprint(tests, url_prefix="/test")


    return app

from app import db_models
