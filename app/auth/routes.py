from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from app.auth import bp
from app.models import Utente


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('orders.lista'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        utente = Utente.query.filter_by(email=email).first()

        if utente and utente.attivo and check_password_hash(utente.password_hash, password):
            login_user(utente, remember=request.form.get('ricordami') == 'on')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('orders.lista'))

        flash('Email o password non validi.', 'danger')

    return render_template('auth/login.html')


@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
