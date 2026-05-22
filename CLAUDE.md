# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Web application (Flask + Python) for managing internal purchase orders ("ordini interni") at Archivis SpA. Orders follow an approval workflow and can be exported as DOCX or PDF.

## Commands

```bash
# Activate virtualenv
workon ordini_interni

# Run development server
python run.py

# Run with explicit venv
/home/daniele/.virtualenvs/ordini_interni/bin/python run.py
```

The app starts at `http://localhost:5000`. Default admin: `admin@archivispa.it` / `admin123`.

## Architecture

**Stack:** Flask 3, SQLAlchemy (SQLite), Flask-Login, Flask-Mail, python-docx, WeasyPrint, Bootstrap 5 CDN.

**Blueprint layout:**
- `app/auth/` — login/logout
- `app/orders/` — CRUD orders, DOCX/PDF export, submit-for-approval
- `app/admin/` — approve/reject orders, manage users and suppliers

**Key models (`app/models.py`):**
- `Utente` — users with `ruolo` ('admin'|'utente'), `attivo` flag
- `Fornitore` — supplier list, with `attivo` flag
- `Ordine` — order header; `numero` is a global auto-increment (not annual reset); `stato` drives the workflow: `bozza → in_attesa → approvato|rifiutato`
- `ArticoloOrdine` — line items; `totale` is computed (`quantita × prezzo_unitario`), sconto is per-row

**Workflow:**
1. User creates order (stato=`bozza`)
2. User clicks "Invia per approvazione" → stato=`in_attesa`, email sent to all admins
3. Admin approves → stato=`approvato`, email to creator/richiedente/emesso_da, CC all admins
4. Admin rejects → stato=`rifiutato` + `motivo_rifiuto`, same email recipients

**Export (`app/orders/export.py`):**
- `genera_docx()` — builds the document programmatically with python-docx, replicating the existing format (header table with order number/date/issuer/reference, items table with totals)
- `genera_pdf()` — renders `orders/print.html` via WeasyPrint

**Configuration:** `.env` file (see `.env.example`). Company name/address/contact used in DOCX/PDF headers. SMTP settings for email notifications.

**Order number format:** `{numero}{_suffisso} - {tipo}` (e.g. `10309 - P`, `10311_A - P`). Tipo is P or C. Suffisso (A, B…) handles split orders from the same base number.

**Fields NOT in the form** (auto or from config): order number, creation date, year, company header.

## Future: import old data

To import existing `.doc`/`.docx` files, write a script using `python-docx` that:
1. Parses the filename for number, type, supplier
2. Reads Table 0 for date, issuer, reference
3. Reads Table 1 for line items
4. Creates `Ordine` + `ArticoloOrdine` records with `stato='approvato'`
