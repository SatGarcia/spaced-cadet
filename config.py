import os
import logging

SECRET_KEY = 'dev'
DATABASE_URI = 'sqlite:///:memory:'
DATABASE_VERBOSE = False
REDIS_URL = 'redis://'
SERVER_NAME = 'localhost:5000'
APPLICATION_ROOT = '/cadet'
LOGGING_LEVEL=logging.INFO
EMAIL_ERRORS = False
