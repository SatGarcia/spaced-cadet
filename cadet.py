from os import environ
from app import create_app

config_class = environ.get('APP_CONFIG_CLASS', 'config.DevelopmentConfig')

app = create_app(config_class)
