from flask import render_template, current_app
from flask_mail import Message
from app import mail
from app.models import Utente


def _admin_emails():
    return [u.email for u in Utente.query.filter_by(ruolo='admin', attivo=True).all()]


def invia_notifica_invio(ordine):
    """Email agli admin quando un ordine viene inviato per approvazione."""
    admins = _admin_emails()
    if not admins:
        return

    msg = Message(
        subject=f'[Ordini] Nuovo ordine {ordine.numero_completo} in attesa di approvazione',
        recipients=admins,
    )
    msg.html = render_template('email/ordine_inviato.html', ordine=ordine,
                               cfg=current_app.config)
    mail.send(msg)


def invia_notifica_approvato(ordine):
    """Email al richiedente + emittente + CC admin."""
    destinatari = list({ordine.richiedente.email, ordine.emesso_da.email,
                        ordine.creato_da.email})
    cc = _admin_emails()

    msg = Message(
        subject=f'[Ordini] Ordine {ordine.numero_completo} APPROVATO',
        recipients=destinatari,
        cc=cc,
    )
    msg.html = render_template('email/ordine_approvato.html', ordine=ordine,
                               cfg=current_app.config)
    mail.send(msg)


def invia_notifica_rifiutato(ordine):
    """Email al richiedente + emittente + CC admin."""
    destinatari = list({ordine.richiedente.email, ordine.emesso_da.email,
                        ordine.creato_da.email})
    cc = _admin_emails()

    msg = Message(
        subject=f'[Ordini] Ordine {ordine.numero_completo} RIFIUTATO',
        recipients=destinatari,
        cc=cc,
    )
    msg.html = render_template('email/ordine_rifiutato.html', ordine=ordine,
                               cfg=current_app.config)
    mail.send(msg)


def invia_notifica_esito(ordine):
    if ordine.stato == 'approvato':
        invia_notifica_approvato(ordine)
    elif ordine.stato == 'rifiutato':
        invia_notifica_rifiutato(ordine)
