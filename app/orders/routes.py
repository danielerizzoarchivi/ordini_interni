from datetime import datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO

from flask import (render_template, redirect, url_for, flash, request,
                   current_app, send_file, abort)
from flask_login import login_required, current_user

from app import db
from app.models import Ordine, ArticoloOrdine, Fornitore, Utente
from app.orders import bp
from app.orders.export import genera_docx, genera_pdf
from app.orders.email import invia_notifica_invio, invia_notifica_esito


def _prossimo_numero(anno):
    ultimo = (db.session.query(db.func.max(Ordine.numero))
              .filter(Ordine.anno == anno).scalar())
    return (ultimo or 0) + 1


def _salva_articoli(ordine, form):
    ArticoloOrdine.query.filter_by(ordine_id=ordine.id).delete()
    descrizioni = request.form.getlist('desc[]')
    qtà = request.form.getlist('qta[]')
    prezzi = request.form.getlist('prezzo[]')
    sconti = request.form.getlist('sconto[]')

    for i, desc in enumerate(descrizioni):
        if not desc.strip():
            continue
        try:
            qta_val = Decimal(qtà[i].replace(',', '.')) if i < len(qtà) else Decimal('1')
            prezzo_val = Decimal(prezzi[i].replace(',', '.')) if i < len(prezzi) else Decimal('0')
            sconto_val = Decimal(sconti[i].replace(',', '.')) if i < len(sconti) and sconti[i].strip() else Decimal('0')
        except (InvalidOperation, IndexError):
            qta_val, prezzo_val, sconto_val = Decimal('1'), Decimal('0'), Decimal('0')

        art = ArticoloOrdine(
            ordine_id=ordine.id,
            posizione=i,
            descrizione=desc.strip(),
            quantita=qta_val,
            prezzo_unitario=prezzo_val,
            sconto=sconto_val,
        )
        db.session.add(art)


@bp.route('/')
@login_required
def lista():
    anno = request.args.get('anno', datetime.now().year, type=int)
    stato = request.args.get('stato', '')

    q = Ordine.query.filter(Ordine.anno == anno)
    if not current_user.is_admin:
        q = q.filter(Ordine.creato_da_id == current_user.id)
    if stato:
        q = q.filter(Ordine.stato == stato)

    ordini = q.order_by(Ordine.numero.desc()).all()
    anni = db.session.query(Ordine.anno).distinct().order_by(Ordine.anno.desc()).all()
    anni = [a[0] for a in anni] or [datetime.now().year]

    return render_template('orders/list.html', ordini=ordini, anno=anno,
                           anni=anni, stato=stato)


@bp.route('/ordini/nuovo', methods=['GET', 'POST'])
@login_required
def nuovo():
    fornitori = Fornitore.query.filter_by(attivo=True).order_by(Fornitore.nome).all()
    utenti = Utente.query.filter_by(attivo=True).order_by(Utente.cognome).all()

    if request.method == 'POST':
        anno = datetime.now().year
        numero = _prossimo_numero(anno)

        fornitore_id = request.form.get('fornitore_id') or None
        fornitore_nome = request.form.get('fornitore_nome', '').strip()
        if fornitore_id:
            f = db.session.get(Fornitore, int(fornitore_id))
            fornitore_nome = f.nome if f else fornitore_nome

        ordine = Ordine(
            numero=numero,
            anno=anno,
            suffisso=request.form.get('suffisso', '').strip().upper() or None,
            tipo=request.form.get('tipo', 'P'),
            fornitore_id=int(fornitore_id) if fornitore_id else None,
            fornitore_nome=fornitore_nome,
            richiedente_id=int(request.form.get('richiedente_id', current_user.id)),
            emesso_da_id=int(request.form.get('emesso_da_id', current_user.id)),
            riferimento=request.form.get('riferimento', '').strip(),
            pagamento=request.form.get('pagamento', '').strip(),
            consegna=request.form.get('consegna', '').strip(),
            note=request.form.get('note', '').strip() or None,
            stato='bozza',
            creato_da_id=current_user.id,
        )
        db.session.add(ordine)
        db.session.flush()
        _salva_articoli(ordine, request.form)
        db.session.commit()
        flash(f'Ordine {ordine.numero_completo} creato.', 'success')
        return redirect(url_for('orders.dettaglio', id=ordine.id))

    return render_template('orders/form.html', ordine=None,
                           fornitori=fornitori, utenti=utenti)


@bp.route('/ordini/<int:id>')
@login_required
def dettaglio(id):
    ordine = db.session.get(Ordine, id)
    if not ordine:
        abort(404)
    if not current_user.is_admin and ordine.creato_da_id != current_user.id:
        abort(403)
    return render_template('orders/view.html', ordine=ordine)


@bp.route('/ordini/<int:id>/modifica', methods=['GET', 'POST'])
@login_required
def modifica(id):
    ordine = db.session.get(Ordine, id)
    if not ordine:
        abort(404)
    if not current_user.is_admin and ordine.creato_da_id != current_user.id:
        abort(403)
    if ordine.stato not in ('bozza', 'rifiutato'):
        flash('L\'ordine non è modificabile in questo stato.', 'warning')
        return redirect(url_for('orders.dettaglio', id=id))

    fornitori = Fornitore.query.filter_by(attivo=True).order_by(Fornitore.nome).all()
    utenti = Utente.query.filter_by(attivo=True).order_by(Utente.cognome).all()

    if request.method == 'POST':
        fornitore_id = request.form.get('fornitore_id') or None
        fornitore_nome = request.form.get('fornitore_nome', '').strip()
        if fornitore_id:
            f = db.session.get(Fornitore, int(fornitore_id))
            fornitore_nome = f.nome if f else fornitore_nome

        ordine.suffisso = request.form.get('suffisso', '').strip().upper() or None
        ordine.tipo = request.form.get('tipo', 'P')
        ordine.fornitore_id = int(fornitore_id) if fornitore_id else None
        ordine.fornitore_nome = fornitore_nome
        ordine.richiedente_id = int(request.form.get('richiedente_id', current_user.id))
        ordine.emesso_da_id = int(request.form.get('emesso_da_id', current_user.id))
        ordine.riferimento = request.form.get('riferimento', '').strip()
        ordine.pagamento = request.form.get('pagamento', '').strip()
        ordine.consegna = request.form.get('consegna', '').strip()
        ordine.note = request.form.get('note', '').strip() or None
        ordine.stato = 'bozza'
        ordine.motivo_rifiuto = None

        _salva_articoli(ordine, request.form)
        db.session.commit()
        flash('Ordine aggiornato.', 'success')
        return redirect(url_for('orders.dettaglio', id=ordine.id))

    return render_template('orders/form.html', ordine=ordine,
                           fornitori=fornitori, utenti=utenti)


@bp.route('/ordini/<int:id>/invia', methods=['POST'])
@login_required
def invia(id):
    ordine = db.session.get(Ordine, id)
    if not ordine or ordine.stato != 'bozza':
        abort(400)
    if not current_user.is_admin and ordine.creato_da_id != current_user.id:
        abort(403)
    if not ordine.articoli:
        flash('Aggiungi almeno un articolo prima di inviare.', 'warning')
        return redirect(url_for('orders.dettaglio', id=id))

    ordine.stato = 'in_attesa'
    db.session.commit()

    try:
        invia_notifica_invio(ordine)
    except Exception as e:
        current_app.logger.error(f'Errore email invio ordine {id}: {e}')

    flash('Ordine inviato per approvazione.', 'success')
    return redirect(url_for('orders.dettaglio', id=id))


@bp.route('/ordini/<int:id>/stampa')
@login_required
def stampa(id):
    ordine = db.session.get(Ordine, id)
    if not ordine:
        abort(404)
    if not current_user.is_admin and ordine.creato_da_id != current_user.id:
        abort(403)
    cfg = current_app.config
    return render_template('orders/print.html', ordine=ordine, cfg=cfg)


@bp.route('/ordini/<int:id>/esporta/docx')
@login_required
def esporta_docx(id):
    ordine = db.session.get(Ordine, id)
    if not ordine:
        abort(404)
    if not current_user.is_admin and ordine.creato_da_id != current_user.id:
        abort(403)

    doc_bytes = genera_docx(ordine, current_app.config)
    nome_file = f'{ordine.numero_completo} {ordine.fornitore_nome}.docx'
    return send_file(
        BytesIO(doc_bytes),
        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        as_attachment=True,
        download_name=nome_file,
    )


@bp.route('/ordini/<int:id>/esporta/pdf')
@login_required
def esporta_pdf(id):
    ordine = db.session.get(Ordine, id)
    if not ordine:
        abort(404)
    if not current_user.is_admin and ordine.creato_da_id != current_user.id:
        abort(403)

    pdf_bytes = genera_pdf(ordine, current_app)
    nome_file = f'{ordine.numero_completo} {ordine.fornitore_nome}.pdf'
    return send_file(
        BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=nome_file,
    )
