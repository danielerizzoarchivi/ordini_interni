import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///ordini.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'localhost')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'ordini@archivispa.it')

    COMPANY_NAME = os.environ.get('COMPANY_NAME', 'Archivi SpA')
    COMPANY_ADDRESS = os.environ.get('COMPANY_ADDRESS', '')
    COMPANY_EMAIL = os.environ.get('COMPANY_EMAIL', '')
    COMPANY_PHONE = os.environ.get('COMPANY_PHONE', '')
