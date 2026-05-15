
"""
Application bancaire (style BNP) - Flask demo
Avec envoi de confirmation PDF par email (Resend + ReportLab)
"""

import os
import io
import zipfile
import logging
from datetime import datetime
from functools import wraps

import resend
from dotenv import load_dotenv
from flask import (
    Flask, flash, redirect, render_template, request,
    send_file, session, url_for,
)
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret")

RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "noreply@lre-certif.fr")

if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY

# ---------------------------------------------------------------------------
# Données factices
# ---------------------------------------------------------------------------
DEMO_USER = {
   "identifiant": "990303",
    "password": "0275",
    "nom": "JEAN MICHEL",
    "email": "jean.michel@gmail.com",
    "agence": "Paris Opéra - 00821",
    "client_depuis": "Mars 2014",
}

COMPTES = [
    {"id": "cc", "libelle": "Compte de Chèques", "iban": "FR76 3000 4000 5000 0001 2345 678", "solde": 100000, "type": "courant"},
    {"id": "livret-a", "libelle": "Livret A", "iban": "FR76 3000 4000 5000 0009 8765 432", "solde": 100000, "type": "epargne"},
    {"id": "ldds", "libelle": "Livret de Développement Durable", "iban": "FR76 3000 4000 5000 0005 5544 332", "solde": 50000.00, "type": "epargne"},
    {"id": "pea", "libelle": "PEA Performance", "iban": "FR76 3000 4000 5000 0007 7766 554", "solde": 45670.88, "type": "titres"},
]

OPERATIONS = [
    {"date": "12/02/2026", "libelle": "CB CARREFOUR PARIS", "montant": -68.40, "categorie": "Courses"},
    {"date": "11/02/2026", "libelle": "VIREMENT SALAIRE SOCIETE XYZ", "montant": 3250.00, "categorie": "Revenus"},
    {"date": "10/02/2026", "libelle": "PRLV EDF ENERGIE", "montant": -89.50, "categorie": "Énergie"},
    {"date": "09/02/2026", "libelle": "CB AMAZON EU", "montant": -42.99, "categorie": "Achats"},
    {"date": "08/02/2026", "libelle": "RETRAIT DAB RUE DE RIVOLI", "montant": -100.00, "categorie": "Espèces"},
    {"date": "07/02/2026", "libelle": "PRLV LOYER SCI MARAIS", "montant": -1200.00, "categorie": "Logement"},
    {"date": "06/02/2026", "libelle": "VIREMENT REÇU - M. MARTIN", "montant": 250.00, "categorie": "Virements"},
    {"date": "05/02/2026", "libelle": "CB SNCF CONNECT", "montant": -78.00, "categorie": "Transport"},
    {"date": "04/02/2026", "libelle": "PRLV ORANGE MOBILE", "montant": -24.99, "categorie": "Télécom"},
    {"date": "03/02/2026", "libelle": "CB BOULANGERIE DUPAIN", "montant": -7.80, "categorie": "Restauration"},
]

BENEFICIAIRES = [
    {"nom": "Marie Dupont", "iban": "FR76 1027 8060 4100 0203 0405 060", "banque": "Crédit Mutuel"},
    {"nom": "Sophie Martin", "iban": "FR76 3000 3030 4000 0506 0708 091", "banque": "Société Générale"},
    {"nom": "SCI Marais Invest", "iban": "FR76 1820 6002 5070 1112 1314 151", "banque": "Crédit Agricole"},
    {"nom": "Lucas Bernard", "iban": "FR76 1469 0000 0116 1718 1920 212", "banque": "LCL"},
    {"nom": "EDF Énergie", "iban": "FR76 3000 4001 0322 2324 2526 272", "banque": "BNP Paribas"},
]

PRELEVEMENTS = [
    {"creancier": "EDF Énergie", "montant": 89.50, "frequence": "Mensuel", "prochain": "10/03/2026", "statut": "Actif"},
    {"creancier": "Orange Mobile", "montant": 24.99, "frequence": "Mensuel", "prochain": "04/03/2026", "statut": "Actif"},
    {"creancier": "SCI Marais (Loyer)", "montant": 1200.00, "frequence": "Mensuel", "prochain": "07/03/2026", "statut": "Actif"},
    {"creancier": "Netflix", "montant": 17.99, "frequence": "Mensuel", "prochain": "15/02/2026", "statut": "Actif"},
    {"creancier": "Assurance MAIF Auto", "montant": 64.20, "frequence": "Mensuel", "prochain": "20/02/2026", "statut": "Actif"},
    {"creancier": "Impôts - Prélèvement source", "montant": 412.00, "frequence": "Mensuel", "prochain": "28/02/2026", "statut": "Actif"},
]

EPARGNE = [
    {"produit": "Livret A", "solde": 22890.10, "taux": "3,00 %", "plafond": 22950.00},
    {"produit": "LDDS", "solde": 12000.00, "taux": "3,00 %", "plafond": 12000.00},
    {"produit": "PEL 2020", "solde": 34560.00, "taux": "1,00 %", "plafond": 61200.00},
    {"produit": "Assurance-Vie Multisupport", "solde": 78450.50, "taux": "2,80 %", "plafond": None},
]

CREDITS = [
    {"type": "Prêt immobilier", "capital_initial": 280000, "restant": 198540.20, "mensualite": 1485.30, "taux": "1,85 %", "fin": "08/2041"},
    {"type": "Prêt auto", "capital_initial": 22000, "restant": 8760.40, "mensualite": 367.50, "taux": "3,40 %", "fin": "11/2027"},
]

ASSURANCES = [
    {"contrat": "Assurance Habitation Confort", "couverture": "Résidence principale - Paris 4e", "cotisation": 28.40, "echeance": "01/2027"},
    {"contrat": "Assurance Auto Tous Risques", "couverture": "Peugeot 308 - AB-123-CD", "cotisation": 64.20, "echeance": "06/2026"},
    {"contrat": "Prévoyance Famille", "couverture": "Décès / Invalidité", "cotisation": 42.10, "echeance": "12/2026"},
    {"contrat": "Garantie Moyens de Paiement", "couverture": "Cartes & chéquiers", "cotisation": 3.50, "echeance": "Mensuelle"},
]

SERVICES = [
    {"nom": "Carte Visa Premier", "description": "Plafond 6 000 € / 30 jours", "icone": "credit-card"},
    {"nom": "Paiement mobile", "description": "Apple Pay, Google Pay, Paylib", "icone": "smartphone"},
    {"nom": "Alertes SMS", "description": "Notifications opérations & solde", "icone": "bell"},
    {"nom": "Chéquier", "description": "Commande en ligne", "icone": "file-text"},
    {"nom": "Coffre numérique", "description": "Stockage sécurisé de documents", "icone": "lock"},
    {"nom": "Devises", "description": "Commande de devises étrangères", "icone": "globe"},
]

MESSAGES = [
    {"de": "Conseiller - M. Lefebvre", "sujet": "Votre rendez-vous du 18/02", "date": "12/02/2026", "lu": False},
    {"de": "Service Cartes", "sujet": "Renouvellement de votre carte Visa Premier", "date": "08/02/2026", "lu": False},
    {"de": "Service Épargne", "sujet": "Nouvelle offre PEL - Taux préférentiel", "date": "05/02/2026", "lu": True},
    {"de": "Sécurité", "sujet": "Connexion depuis un nouvel appareil", "date": "01/02/2026", "lu": True},
]

SECTIONS = [
    {"id": "accueil", "label": "Accueil", "icone": "home"},
    {"id": "releve", "label": "Relevé", "icone": "file-text"},
    {"id": "beneficiaires", "label": "Bénéficiaires", "icone": "users"},
    {"id": "virement", "label": "Virement", "icone": "send"},
    {"id": "prelevements", "label": "Prélèvements", "icone": "repeat"},
    {"id": "epargne", "label": "Épargne", "icone": "piggy-bank"},
    {"id": "credits", "label": "Crédits", "icone": "landmark"},
    {"id": "assurances", "label": "Assurances", "icone": "shield"},
    {"id": "services", "label": "Services", "icone": "settings"},
    {"id": "domiciliation", "label": "Domiciliation", "icone": "map-pin"},
    {"id": "messagerie", "label": "Messagerie", "icone": "mail"},
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("authenticated"):
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def send_email(recipient, subject, html, attachments=None):
    """Envoie un email via Resend. attachments = [{filename, content (bytes)}]"""
    if not RESEND_API_KEY:
        logger.warning("RESEND_API_KEY non configurée - email ignoré")
        return False
    try:
        params = {
            "from": SENDER_EMAIL,
            "to": [recipient],
            "subject": subject,
            "html": html,
        }
        if attachments:
            params["attachments"] = [
                {"filename": a["filename"], "content": list(a["content"])}
                for a in attachments
            ]
        result = resend.Emails.send(params)
        logger.info("Email envoyé id=%s (avec %d PJ)", result.get("id"), len(attachments or []))
        return True
    except Exception as exc:
        logger.error("Echec envoi email: %s", exc)
        return False


def generate_virement_pdf(beneficiaire, iban, montant, motif,
                          solde_avant, solde_apres, reference):
    """Génère un PDF de confirmation de virement, retourne les bytes."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
        title="Confirmation de virement",
    )

    brand_green = colors.HexColor("#00915a")
    brand_dark = colors.HexColor("#006a40")
    light_bg = colors.HexColor("#e7f5ee")
    gray_dark = colors.HexColor("#3f4744")
    gray_light = colors.HexColor("#e5e8e7")

    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Heading1"],
                        fontName="Helvetica-Bold", fontSize=20,
                        textColor=colors.white, spaceAfter=4)
    sub = ParagraphStyle("sub", parent=styles["Normal"],
                         fontName="Helvetica", fontSize=10,
                         textColor=colors.HexColor("#d1f0e0"))
    body = ParagraphStyle("body", parent=styles["Normal"],
                          fontName="Helvetica", fontSize=10.5,
                          textColor=gray_dark, leading=15)
    footer = ParagraphStyle("footer", parent=styles["Normal"],
                            fontName="Helvetica", fontSize=8,
                            textColor=colors.HexColor("#9ca3a0"), alignment=1)

    story = []

    # En-tête vert
    header = Table(
        [[Paragraph("Confirmation de virement", h1),
          Paragraph(f"Référence : {reference}", sub)]],
        colWidths=[12 * cm, 5 * cm],
    )
    header.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), brand_green),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 16),
        ("RIGHTPADDING", (0, 0), (-1, -1), 16),
        ("TOPPADDING", (0, 0), (-1, -1), 18),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 18),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
    ]))
    story.append(header)
    story.append(Spacer(1, 0.6 * cm))

    now_str = datetime.now().strftime("%d/%m/%Y à %H:%M")
    story.append(Paragraph(
        f"<b>BNP PARIBAS</b> &nbsp;·&nbsp; Ordre exécuté le <b>{now_str}</b>",
        body,
    ))
    story.append(Spacer(1, 0.5 * cm))

    # Tableau détails
    data = [
        ["Bénéficiaire", beneficiaire],
        ["IBAN", iban],
        ["Montant", f"{montant:.2f} €"],
        ["Motif", motif or "—"],
        ["Compte débité", "Compte de Chèques"],
        ["Solde avant opération", f"{solde_avant:.2f} €"],
        ["Solde après opération", f"{solde_apres:.2f} €"],
        ["Date d'exécution", now_str],
        ["Référence", reference],
    ]
    tbl = Table(data, colWidths=[5.5 * cm, 11.5 * cm])
    tbl.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (0, -1), gray_dark),
        ("TEXTCOLOR", (1, 0), (1, -1), colors.HexColor("#131816")),
        ("BACKGROUND", (0, 0), (0, -1), light_bg),
        ("ROWBACKGROUNDS", (1, 0), (1, -1), [colors.white, colors.HexColor("#f8faf9")]),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, gray_light),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        # Mise en évidence du montant
        ("FONTNAME", (1, 2), (1, 2), "Helvetica-Bold"),
        ("TEXTCOLOR", (1, 2), (1, 2), brand_dark),
        ("FONTSIZE", (1, 2), (1, 2), 13),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 0.8 * cm))

    # Cadre information
    info = Table(
        [[Paragraph(
            "<b>Information</b> &nbsp;·&nbsp; Cet ordre de virement a été pris en compte et "
            "sera transmis au système SEPA. Le délai de traitement standard est de J+1 ouvré. "
            "En cas de question, contactez votre conseiller via la messagerie sécurisée.",
            body,
        )]],
        colWidths=[17 * cm],
    )
    info.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), light_bg),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))
    story.append(info)
    story.append(Spacer(1, 1.2 * cm))

    story.append(Paragraph(
        "BNP PARIBAS — Démonstration · Document généré automatiquement, ne nécessite pas de signature.",
        footer,
    ))
    story.append(Paragraph("© 2026 BNP PARIBAS · Tous droits réservés", footer))

    doc.build(story)
    return buf.getvalue()


def virement_email_html(beneficiaire, iban, montant, motif):
    return f"""
    <table width="100%" cellpadding="0" cellspacing="0" style="font-family: Arial, sans-serif; background:#f4f6f5; padding:24px;">
      <tr><td align="center">
        <table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff; border-radius:8px; overflow:hidden;">
          <tr><td style="background:#00915a; padding:24px; color:#ffffff;">
            <h1 style="margin:0; font-size:20px;">Confirmation de virement</h1>
          </td></tr>
          <tr><td style="padding:24px; color:#333;">
            <p>Bonjour,</p>
            <p>Nous vous confirmons la prise en compte de votre ordre de virement. Vous trouverez le détail complet dans le PDF en pièce jointe.</p>
            <table width="100%" cellpadding="8" style="border-collapse:collapse; margin:16px 0;">
              <tr><td style="border-bottom:1px solid #e5e7eb;"><strong>Bénéficiaire</strong></td><td style="border-bottom:1px solid #e5e7eb;">{beneficiaire}</td></tr>
              <tr><td style="border-bottom:1px solid #e5e7eb;"><strong>IBAN</strong></td><td style="border-bottom:1px solid #e5e7eb;">{iban}</td></tr>
              <tr><td style="border-bottom:1px solid #e5e7eb;"><strong>Montant</strong></td><td style="border-bottom:1px solid #e5e7eb;">{montant:.2f} €</td></tr>
              <tr><td><strong>Motif</strong></td><td>{motif or '—'}</td></tr>
            </table>
            <p style="color:#6b7280; font-size:13px;">Cet email est généré par votre Espace Client. Pour toute question, contactez votre conseiller.</p>
          </td></tr>
          <tr><td style="background:#f4f6f5; padding:16px; text-align:center; color:#6b7280; font-size:12px;">
            © 2026 Démo Banque — Tous droits réservés
          </td></tr>
        </table>
      </td></tr>
    </table>
    """


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/", methods=["GET"])
def index():
    if session.get("authenticated"):
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None

    demo_public = {
        "nom": DEMO_USER["nom"],
        "email": DEMO_USER["email"]
    }

    if request.method == "POST":
        identifiant = request.form.get("identifiant", "").strip()
        password = request.form.get("password", "").strip()

        if identifiant == DEMO_USER["identifiant"] and password == DEMO_USER["password"]:
            session["authenticated"] = True
            session["user"] = demo_public
            return redirect(url_for("dashboard"))

        error = "Identifiant ou mot de passe incorrect."

    return render_template("login.html", error=error, demo=demo_public)


@app.route("/dashboard", methods=["GET"])
@login_required
def dashboard():
    section = request.args.get("section", "accueil")
    total_solde = sum(c["solde"] for c in COMPTES)
    return render_template(
        "dash.html",
        user=session.get("user"), demo_user=DEMO_USER,
        sections=SECTIONS, active_section=section,
        comptes=COMPTES, operations=OPERATIONS, beneficiaires=BENEFICIAIRES,
        prelevements=PRELEVEMENTS, epargne=EPARGNE, credits=CREDITS,
        assurances=ASSURANCES, services=SERVICES, messages=MESSAGES,
        total_solde=total_solde, today=datetime.now().strftime("%d/%m/%Y"),
    )


@app.route("/virement", methods=["POST"])
@login_required
def virement():
    beneficiaire = request.form.get("beneficiaire", "").strip()
    iban = request.form.get("iban", "").strip()
    montant_raw = request.form.get("montant", "0").strip().replace(",", ".")
    motif = request.form.get("motif", "").strip()
    email_dest = request.form.get("email", "").strip() or DEMO_USER["email"]

    try:
        montant = float(montant_raw)
    except ValueError:
        montant = 0.0

    if not beneficiaire or not iban or montant <= 0:
        flash("Veuillez renseigner un bénéficiaire, un IBAN et un montant valide.", "error")
        return redirect(url_for("dashboard", section="virement"))

    # Compte à débiter = compte de chèques
    compte = COMPTES[0]
    if montant > compte["solde"]:
        flash(
            f"Solde insuffisant. Solde disponible : {compte['solde']:.2f} € — "
            f"Virement demandé : {montant:.2f} €.",
            "error",
        )
        return redirect(url_for("dashboard", section="virement"))

    # Débit + écriture comptable
    solde_avant = compte["solde"]
    compte["solde"] = round(compte["solde"] - montant, 2)
    solde_apres = compte["solde"]
    reference = f"VIR-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    libelle_op = f"VIREMENT {beneficiaire.upper()}"
    if motif:
        libelle_op += f" - {motif.upper()}"
    OPERATIONS.insert(0, {
        "date": datetime.now().strftime("%d/%m/%Y"),
        "libelle": libelle_op,
        "montant": -montant,
        "categorie": "Virements",
    })

    # Génération PDF + envoi email avec pièce jointe
    pdf_bytes = generate_virement_pdf(
        beneficiaire=beneficiaire, iban=iban, montant=montant, motif=motif,
        solde_avant=solde_avant, solde_apres=solde_apres, reference=reference,
    )
    html = virement_email_html(beneficiaire, iban, montant, motif)
    pdf_filename = f"confirmation-virement-{reference}.pdf"
    sent = send_email(
        email_dest,
        f"Confirmation de virement - {montant:.2f} €",
        html,
        attachments=[{"filename": pdf_filename, "content": pdf_bytes}],
    )

    base_msg = (
        f"Virement de {montant:.2f} € exécuté. "
        f"Nouveau solde du compte de chèques : {compte['solde']:.2f} €."
    )
    if sent:
        flash(f"{base_msg} Confirmation PDF envoyée à {email_dest}.", "success")
    else:
        flash(f"{base_msg} (email + PDF non envoyés)", "success")

    return redirect(url_for("dashboard", section="virement"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/download")
def download_source():
    """Génère un ZIP contenant l'ensemble du code source du projet."""
    project_root = os.path.dirname(os.path.abspath(__file__))
    files_to_include = [
        "app.py",
        "requirements.txt",
        "README.md",
        ".env",
        "templates/login.html",
        "templates/dash.html",
    ]
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel_path in files_to_include:
            abs_path = os.path.join(project_root, rel_path)
            if os.path.exists(abs_path):
                zf.write(abs_path, arcname=f"app-bancaire/{rel_path}")
    buffer.seek(0)
    return send_file(
        buffer,
        mimetype="application/zip",
        as_attachment=True,
        download_name="app-bancaire.zip",
    )


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)