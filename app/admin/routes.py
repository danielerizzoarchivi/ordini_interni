from datetime import datetime
from functools import wraps

from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash

from app import db
from app.admin import bp
from app.models import Utente, Fornitore, Ordine
from app.orders.email import invia_notifica_esito


def admin_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated


# ---- Dashboard admin ----

@bp.route('/')
@admin_required
def dashboard():
    in_attesa = Ordine.query.filter_by(stato='in_attesa').order_by(Ordine.creato_il).all()
    return render_template('admin/dashboard.html', in_attesa=in_attesa)


# ---- Gestione ordini ----

@bp.route('/ordini/<int:id>/approva', methods=['POST'])
@admin_required
def approva(id):
    ordine = db.session.get(Ordine, id)
    if not ordine or ordine.stato != 'in_attesa':
        abort(400)

    ordine.stato = 'approvato'
    ordine.approvato_da_id = current_user.id
    ordine.approvato_il = datetime.utcnow()
    ordine.motivo_rifiuto = None
    db.session.commit()

    try:
        invia_notifica_esito(ordine)
    except Exception as e:
        flash(f'Ordine approvato ma errore email: {e}', 'warning')
    else:
        flash(f'Ordine {ordine.numero_completo} approvato. Notifica inviata.', 'success')

    return redirect(request.referrer or url_for('admin.dashboard'))


@bp.route('/ordini/<int:id>/rifiuta', methods=['POST'])
@admin_required
def rifiuta(id):
    ordine = db.session.get(Ordine, id)
    if not ordine or ordine.stato != 'in_attesa':
        abort(400)

    motivo = request.form.get('motivo', '').strip()
    if not motivo:
        flash('Specifica il motivo del rifiuto.', 'danger')
        return redirect(request.referrer or url_for('admin.dashboard'))

    ordine.stato = 'rifiutato'
    ordine.approvato_da_id = current_user.id
    ordine.approvato_il = datetime.utcnow()
    ordine.motivo_rifiuto = motivo
    db.session.commit()

    try:
        invia_notifica_esito(ordine)
    except Exception as e:
        flash(f'Ordine rifiutato ma errore email: {e}', 'warning')
    else:
        flash(f'Ordine {ordine.numero_completo} rifiutato. Notifica inviata.', 'success')

    return redirect(request.referrer or url_for('admin.dashboard'))


# ---- Gestione utenti ----

@bp.route('/utenti')
@admin_required
def utenti():
    lista = Utente.query.order_by(Utente.cognome, Utente.nome).all()
    return render_template('admin/users.html', utenti=lista)


@bp.route('/utenti/nuovo', methods=['GET', 'POST'])
@admin_required
def nuovo_utente():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        if Utente.query.filter_by(email=email).first():
            flash('Email già in uso.', 'danger')
            return render_template('admin/user_form.html', utente=None)

        u = Utente(
            nome=request.form.get('nome', '').strip(),
            cognome=request.form.get('cognome', '').strip(),
            email=email,
            password_hash=generate_password_hash(request.form.get('password', '')),
            ruolo=request.form.get('ruolo', 'utente'),
            attivo=True,
        )
        db.session.add(u)
        db.session.commit()
        flash(f'Utente {u.nome_completo} creato.', 'success')
        return redirect(url_for('admin.utenti'))

    return render_template('admin/user_form.html', utente=None)


@bp.route('/utenti/<int:id>/modifica', methods=['GET', 'POST'])
@admin_required
def modifica_utente(id):
    utente = db.session.get(Utente, id)
    if not utente:
        abort(404)

    if request.method == 'POST':
        utente.nome = request.form.get('nome', '').strip()
        utente.cognome = request.form.get('cognome', '').strip()
        utente.email = request.form.get('email', '').strip().lower()
        utente.ruolo = request.form.get('ruolo', 'utente')
        nuova_pw = request.form.get('password', '').strip()
        if nuova_pw:
            utente.password_hash = generate_password_hash(nuova_pw)
        db.session.commit()
        flash('Utente aggiornato.', 'success')
        return redirect(url_for('admin.utenti'))

    return render_template('admin/user_form.html', utente=utente)


@bp.route('/utenti/<int:id>/toggle', methods=['POST'])
@admin_required
def toggle_utente(id):
    utente = db.session.get(Utente, id)
    if not utente:
        abort(404)
    if utente.id == current_user.id:
        flash('Non puoi disabilitare te stesso.', 'danger')
        return redirect(url_for('admin.utenti'))
    utente.attivo = not utente.attivo
    db.session.commit()
    stato = 'abilitato' if utente.attivo else 'disabilitato'
    flash(f'Utente {utente.nome_completo} {stato}.', 'success')
    return redirect(url_for('admin.utenti'))


# ---- Gestione fornitori ----

@bp.route('/fornitori')
@admin_required
def fornitori():
    lista = Fornitore.query.order_by(Fornitore.nome).all()
    return render_template('admin/suppliers.html', fornitori=lista)


@bp.route('/fornitori/nuovo', methods=['POST'])
@admin_required
def nuovo_fornitore():
    nome = request.form.get('nome', '').strip()
    if nome:
        if not Fornitore.query.filter_by(nome=nome).first():
            db.session.add(Fornitore(nome=nome))
            db.session.commit()
            flash(f'Fornitore "{nome}" aggiunto.', 'success')
        else:
            flash('Fornitore già presente.', 'warning')
    return redirect(url_for('admin.fornitori'))


@bp.route('/fornitori/<int:id>/toggle', methods=['POST'])
@admin_required
def toggle_fornitore(id):
    f = db.session.get(Fornitore, id)
    if not f:
        abort(404)
    f.attivo = not f.attivo
    db.session.commit()
    stato = 'abilitato' if f.attivo else 'disabilitato'
    flash(f'Fornitore "{f.nome}" {stato}.', 'success')
    return redirect(url_for('admin.fornitori'))
