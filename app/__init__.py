from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from config import Config

db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Accedi per continuare.'
    login_manager.login_message_category = 'warning'

    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp)

    from app.orders import bp as orders_bp
    app.register_blueprint(orders_bp)

    from app.admin import bp as admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')

    with app.app_context():
        db.create_all()
        _init_admin()

    return app


def _init_admin():
    from app.models import Utente
    from werkzeug.security import generate_password_hash
    if not Utente.query.filter_by(ruolo='admin').first():
        admin = Utente(
            nome='Amministratore',
            cognome='Sistema',
            email='admin@archivispa.it',
            password_hash=generate_password_hash('admin123'),
            ruolo='admin',
            attivo=True,
        )
        db.session.add(admin)
        db.session.commit()
