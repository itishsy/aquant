from flask import Flask
from flask_login import LoginManager
from common.config import config, Config
import logging
from logging.config import fileConfig
import os

# log_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'conf\\log-app.conf')
# fileConfig(log_file_path)
login_manager = LoginManager()
login_manager.session_protection = 'strong'
login_manager.login_view = 'auth.login'


def get_logger(name):
    return logging.getLogger(name)


def get_basedir():
    return os.path.abspath(os.path.dirname(__file__))


def get_config():
    return config[os.getenv('FLASK_CONFIG') or 'default']


def create_app(config_name):
    app = Flask(__name__, static_url_path=Config.URL_PREFIX)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    login_manager.init_app(app)

    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint, url_prefix=Config.URL_PREFIX)

    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix=Config.URL_PREFIX)

    return app
