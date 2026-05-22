from datetime import datetime
from flask_login import UserMixin
from app import db, login_manager


class Utente(UserMixin, db.Model):
    __tablename__ = 'utenti'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    cognome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(200), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    ruolo = db.Column(db.String(20), default='utente')  # 'admin', 'utente'
    attivo = db.Column(db.Boolean, default=True)
    creato_il = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def nome_completo(self):
        return f'{self.nome} {self.cognome}'

    @property
    def is_admin(self):
        return self.ruolo == 'admin'

    def __repr__(self):
        return f'<Utente {self.email}>'


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Utente, int(user_id))


class Fornitore(db.Model):
    __tablename__ = 'fornitori'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), nullable=False)
    attivo = db.Column(db.Boolean, default=True)
    creato_il = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Fornitore {self.nome}>'


class Ordine(db.Model):
    __tablename__ = 'ordini'
    id = db.Column(db.Integer, primary_key=True)

    # Numerazione
    numero = db.Column(db.Integer, nullable=False)
    anno = db.Column(db.Integer, nullable=False)
    suffisso = db.Column(db.String(5), nullable=True)   # A, B, ...
    tipo = db.Column(db.String(1), nullable=False, default='P')  # P, C

    # Fornitore (nome libero o da lista)
    fornitore_id = db.Column(db.Integer, db.ForeignKey('fornitori.id'), nullable=True)
    fornitore_nome = db.Column(db.String(200), nullable=False)
    fornitore = db.relationship('Fornitore', backref='ordini')

    # Persone
    richiedente_id = db.Column(db.Integer, db.ForeignKey('utenti.id'), nullable=False)
    emesso_da_id = db.Column(db.Integer, db.ForeignKey('utenti.id'), nullable=False)
    richiedente = db.relationship('Utente', foreign_keys=[richiedente_id], backref='ordini_richiesti')
    emesso_da = db.relationship('Utente', foreign_keys=[emesso_da_id], backref='ordini_emessi')

    # Campi ordine
    riferimento = db.Column(db.String(100), nullable=True)
    pagamento = db.Column(db.String(200), nullable=True)
    consegna = db.Column(db.String(200), nullable=True)
    note = db.Column(db.Text, nullable=True)

    # Workflow
    stato = db.Column(db.String(20), default='bozza')  # bozza, in_attesa, approvato, rifiutato
    creato_da_id = db.Column(db.Integer, db.ForeignKey('utenti.id'), nullable=False)
    creato_il = db.Column(db.DateTime, default=datetime.utcnow)
    approvato_da_id = db.Column(db.Integer, db.ForeignKey('utenti.id'), nullable=True)
    approvato_il = db.Column(db.DateTime, nullable=True)
    motivo_rifiuto = db.Column(db.Text, nullable=True)

    creato_da = db.relationship('Utente', foreign_keys=[creato_da_id])
    approvato_da = db.relationship('Utente', foreign_keys=[approvato_da_id])

    articoli = db.relationship('ArticoloOrdine', backref='ordine', cascade='all, delete-orphan',
                                order_by='ArticoloOrdine.posizione')

    @property
    def numero_completo(self):
        suf = f'_{self.suffisso}' if self.suffisso else ''
        return f'{self.numero}{suf} - {self.tipo}'

    @property
    def totale(self):
        return sum(a.totale for a in self.articoli if a.totale)

    @property
    def sconto_totale(self):
        return sum(a.sconto or 0 for a in self.articoli)

    @property
    def totale_netto(self):
        return self.totale - self.sconto_totale

    @property
    def stato_label(self):
        labels = {
            'bozza': 'Bozza',
            'in_attesa': 'In attesa di approvazione',
            'approvato': 'Approvato',
            'rifiutato': 'Rifiutato',
        }
        return labels.get(self.stato, self.stato)

    @property
    def stato_badge(self):
        badges = {
            'bozza': 'secondary',
            'in_attesa': 'warning',
            'approvato': 'success',
            'rifiutato': 'danger',
        }
        return badges.get(self.stato, 'secondary')

    def __repr__(self):
        return f'<Ordine {self.numero_completo}>'


class ArticoloOrdine(db.Model):
    __tablename__ = 'articoli_ordine'
    id = db.Column(db.Integer, primary_key=True)
    ordine_id = db.Column(db.Integer, db.ForeignKey('ordini.id'), nullable=False)
    posizione = db.Column(db.Integer, default=0)
    descrizione = db.Column(db.Text, nullable=False)
    quantita = db.Column(db.Numeric(10, 2), nullable=False, default=1)
    prezzo_unitario = db.Column(db.Numeric(10, 2), nullable=False)
    sconto = db.Column(db.Numeric(10, 2), nullable=True, default=0)

    @property
    def totale(self):
        if self.quantita and self.prezzo_unitario:
            return float(self.quantita) * float(self.prezzo_unitario)
        return 0

    @property
    def totale_netto(self):
        return self.totale - float(self.sconto or 0)
