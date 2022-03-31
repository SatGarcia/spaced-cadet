import os
import logging
from datetime import timedelta

SECRET_KEY = 'dev'

JWT_SECRET_KEY = 'dev'
JWT_COOKIE_SECURE = False
JWT_TOKEN_LOCATION = ["cookies"]
JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)

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
