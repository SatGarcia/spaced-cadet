import os
import logging

SECRET_KEY = 'dev'
JWT_SECRET_KEY = 'dev'
#SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
SQLALCHEMY_DATABASE_URI = 'sqlite:///cadet_db.sqlite'
SQLALCHEMY_TRACK_MODIFICATIONS = False
DATABASE_VERBOSE = False
ELASTICSEARCH_URL = 'http://localhost:9200'
#REDIS_URL = 'redis://'
#SERVER_NAME = 'localhost:5000'
#APPLICATION_ROOT = '/cadet'
LOGGING_LEVEL=logging.INFO
EMAIL_ERRORS = False
MAIL_PORT = 1099
