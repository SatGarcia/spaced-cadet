import os
import logging
from datetime import timedelta

class Config(object):
    TESTING = False
    SECRET_KEY = 'dev'

    JWT_SECRET_KEY = 'dev'
    JWT_TOKEN_LOCATION = ["cookies"]

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SMTP_SERVER = 'localhost'
    LOGGING_LEVEL = logging.ERROR
    EMAIL_ERRORS = False

    ELASTICSEARCH_URL = 'http://localhost:9200'

class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = 'sqlite:///cadet_db.sqlite'
    JWT_COOKIE_SECURE = True
    EMAIL_ERRORS = True
    #SERVER_NAME = 'localhost:5000'
    #APPLICATION_ROOT = '/cadet'

class DevelopmentConfig(Config):
    SQLALCHEMY_DATABASE_URI = 'sqlite:///cadet_db.sqlite'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    LOGGING_LEVEL = logging.DEBUG
    MAIL_PORT = 1099

class TestConfig(object):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
