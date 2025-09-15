# --- Python standard ---
import os
import sqlite3
from datetime import datetime

# --- Packages tiers ---
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    send_from_directory,
    current_app,
    session   
)
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask_babel import Babel, _
from fpdf import FPDF
import smtplib
from email.message import EmailMessage
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

# --- CONFIGURATION ---
app = Flask(__name__)
app.secret_key = "w3V7!Jd9-52d@Xg0pN&zQfLk+Ua7RsYh"
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'png', 'jpg', 'jpeg'}
app.config['BABEL_DEFAULT_LOCALE'] = 'fr'

babel = Babel(app)

# SMTP
SMTP_HOST = "smtp.office365.com"
SMTP_PORT = 587
SMTP_USER = "smartlend@outlook.fr"
SMTP_PASS = "gvjldnjkwrsombbw"

# --- DATABASE ---
DB_NAME = 'smartlend.db'

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

# --- UTILITIES ---
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def ensure_loan_dict(loan):
    """
    Accepte sqlite3.Row ou dict ; renvoie toujours un dict.
    """
    if loan is None:
        return None
    try:
        # sqlite3.Row est mappé en dict facilement
        return dict(loan)
    except Exception:
        return loan if isinstance(loan, dict) else {}

def generate_contract_pdf(loan):
    """
    Génère un PDF professionnel pour le prêt et retourne le chemin du fichier.
    Utilise des textes ASCII (EUR) pour éviter les problèmes d'encodage.
    """
    loan = ensure_loan_dict(loan)
    loan_id = loan.get("id", "unknown")
    filename = f"contract_{loan_id}.pdf"
    upload_folder = app.config.get("UPLOAD_FOLDER", "uploads")
    os.makedirs(upload_folder, exist_ok=True)
    path = os.path.join(upload_folder, filename)

    width, height = A4
    c = canvas.Canvas(path, pagesize=A4)

    # ==== HEADER ====
    c.setFont("Helvetica-Bold", 20)
    c.setFillColor(colors.HexColor("#0d6efd"))  # Bleu fintech premium
    c.drawString(60, height - 80, "SmartLend - Contrat de prêt")
    
    c.setFont("Helvetica", 10)
    c.setFillColor(colors.black)
    c.drawString(60, height - 100, "Email : smartlend@outlook.fr")
    c.drawString(60, height - 115, f"Date : {loan.get('created_at', 'N/A')}")

    # ==== Infos client & prêt ====
    y = height - 150
    line_spacing = 18
    lines = [
        ("Nom", loan.get("fullname", "N/A")),
        ("Email", loan.get("email", "N/A")),
        ("Montant demandé", f"{loan.get('amount', 'N/A')} EUR"),
        ("Frais de dossier", f"{loan.get('fee', 'N/A')} EUR"),
        ("Intérêt calculé", f"{loan.get('interest', 'N/A')} EUR"),
        ("Total à rembourser", f"{loan.get('total', 'N/A')} EUR"),
        ("Durée", f"{loan.get('duration', 'N/A')}"),
        ("Période", f"{loan.get('period', 'N/A')}"),
        ("Compte bancaire (RIB)", loan.get("rib", "N/A")),
        ("Objectif", loan.get("objective", "N/A")),
    ]

    # Ligne de séparation avant les infos
    c.setStrokeColor(colors.HexColor("#0d6efd"))
    c.setLineWidth(1)
    c.line(50, y + 10, width - 50, y + 10)

    for label, value in lines:
        # Label bleu foncé gras
        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(colors.HexColor("#0d6efd"))
        c.drawString(60, y, f"{label} :")
        
        # Valeur noir normal
        c.setFont("Helvetica", 11)
        c.setFillColor(colors.black)
        c.drawString(200, y, str(value))
        y -= line_spacing

        if y < 120:
            c.showPage()
            y = height - 80
            c.setStrokeColor(colors.HexColor("#0d6efd"))
            c.setLineWidth(1)
            c.line(50, y + 10, width - 50, y + 10)
            y -= 20

    # ==== Signatures ====
    y -= 30
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(colors.black)
    c.drawString(60, y, "Signature du client : ____________________________")
    c.drawString(350, y, "Signature SmartLend : _________________________")

    # Ligne sous signatures
    c.setLineWidth(0.5)
    c.line(60, y-2, 250, y-2)
    c.line(350, y-2, 600, y-2)

    # ==== Footer ====
    c.setFont("Helvetica-Oblique", 8)
    c.setFillColor(colors.grey)
    c.drawString(60, 30, "SmartLend © 2025 - smartlend@outlook.fr - www.smartlend.com")

    c.save()
    return path

def send_loan_approval_email(to_addr: str, loan, pdf_path=None):
    """
    Envoie un email professionnel avec le contrat en pièce jointe.
    Retourne True si l'envoi a réussi, False sinon.
    """
    # ---- Infos prêt ----
    loan = ensure_loan_dict(loan)
    fullname = loan.get("fullname", "Client")
    amount = loan.get("amount", 0)
    fee = loan.get("fee", 0)
    interest = loan.get("interest", 0)
    total = loan.get("total", 0)
    rib = loan.get("rib", "N/A")

    subject = "SmartLend — Votre demande a été approuvée"
    body = f"""Bonjour {fullname},

Nous avons le plaisir de vous informer que votre demande de prêt a été approuvée.

Détails :
- Montant demandé : {amount:,.2f} EUR
- Frais de dossier : {fee:,.2f} EUR
- Intérêts : {interest:,.2f} EUR
- Montant total à rembourser : {total:,.2f} EUR
- RIB : {rib}

Vous trouverez en pièce jointe le contrat officiel.

Cordialement,
L'équipe SmartLend
"""

    # -------- Simulation si pas de mot de passe SMTP --------
    if not globals().get("SMTP_PASS"):
        print("[EMAIL SIMULATION] To:", to_addr)
        print("Subject:", subject)
        print(body)
        return True

    # -------- Envoi réel --------
    try:
        msg = EmailMessage()
        msg["From"] = SMTP_USER
        msg["To"] = to_addr
        msg["Subject"] = subject
        msg.set_content(body)

        if pdf_path and os.path.exists(pdf_path):
            with open(pdf_path, "rb") as f:
                data = f.read()
            msg.add_attachment(
                data,
                maintype="application",
                subtype="pdf",
                filename=os.path.basename(pdf_path),
            )

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
            s.starttls()
            s.login(SMTP_USER, SMTP_PASS)
            s.send_message(msg)

        print(">>> Email envoyé avec succès")
        return True

    except Exception as e:
        print("Erreur envoi email:", e)
        return False

def calculate_loan(amount, duration, period):
    """
    Calcule les frais de dossier, les intérêts et le total à rembourser
    pour un prêt donné.
    - amount : montant demandé (float)
    - duration : durée choisie par l'utilisateur (en mois)
    - period : 'mensuel', 'trimestriel', 'semestriel' ou 'annuel'
    """

    # --- Frais de dossier (5 % si <= 60 000 €, sinon 8 %) ---
    if amount <= 60000:
        fee = amount * 0.05
    else:
        fee = amount * 0.08

    # --- Taux annuel ---
    annual_rate = 0.12  # 12 %

    # --- Conversion selon la période ---
    if period == "mensuel":
        rate_per_period = annual_rate / 12      # 1 % par mois
        n_periods = duration                    # nombre de mois
    elif period == "trimestriel":
        rate_per_period = annual_rate / 4       # 3 % par trimestre
        n_periods = duration / 3                # nombre de trimestres
    elif period == "semestriel":
        rate_per_period = annual_rate / 2       # 6 % par semestre
        n_periods = duration / 6                # nombre de semestres
    else:  # annuel
        rate_per_period = annual_rate
        n_periods = duration / 12               # nombre d'années

    # --- Intérêts (simple) ---
    interest = amount * rate_per_period * n_periods

    # --- Total à rembourser ---
    total = amount + fee + interest

    return fee, interest, total
# --- ROUTES ---
@app.route('/')
def index():
    return render_template("index.html")

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method=='POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        hashed_pw = generate_password_hash(password)
        conn = get_db_connection()
        try:
            conn.execute("INSERT INTO users (username,email,password,role) VALUES (?,?,?,?)",
                         (username,email,hashed_pw,'user'))
            conn.commit()
            flash(_("Compte créé avec succès !"),"success")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash(_("Email ou username déjà utilisé"),"danger")
        finally:
            conn.close()
    return render_template("register.html")

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']

            # Redirection selon le rôle
            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('dashboard'))
        else:
            flash(_("Identifiants invalides"), "danger")
    return render_template("login.html")

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'role' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    if session['role']=='admin':
        loans = conn.execute("SELECT * FROM loans").fetchall()
    else:
        loans = conn.execute("SELECT * FROM loans WHERE user_id=?",(session['user_id'],)).fetchall()
    conn.close()
    return render_template("dashboard.html",loans=loans)

@app.route('/apply', methods=['GET','POST'])
def apply_loan():
    if 'role' not in session or session['role']!='user':
        return redirect(url_for('login'))
    if request.method=='POST':
        fullname = request.form['fullname']
        dob = request.form['dob']
        address = request.form['address']
        email = request.form['email']
        amount = float(request.form['amount'])
        duration = int(request.form['duration'])
        period = request.form['period']
        objective = request.form['objective']
        rib = request.form['rib']
        file = request.files['identity']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'],filename)
            file.save(filepath)
        else:
            flash(_("Veuillez fournir une pièce d'identité valide"),"danger")
            return redirect(request.url)

        fee, interest, total = calculate_loan(amount,duration,period)
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""INSERT INTO loans 
                        (user_id,fullname,dob,address,email,amount,duration,period,objective,rib,identity_file,fee,interest,total,status) 
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                     (session['user_id'],fullname,dob,address,email,amount,duration,period,objective,rib,filename,fee,interest,total,'pending'))
        loan_id = cur.lastrowid
        conn.commit()
        conn.close()
        flash(_("Votre demande est enregistrée et en attente d'approbation."),"success")
        return redirect(url_for('loan_confirmation', loan_id=loan_id))
    return render_template("apply.html")

@app.route('/loan/confirmation/<int:loan_id>')
def loan_confirmation(loan_id):
    if 'role' not in session or session['role']!='user':
        return redirect(url_for('login'))
    conn = get_db_connection()
    loan = conn.execute("SELECT * FROM loans WHERE id=? AND user_id=?",(loan_id,session['user_id'])).fetchone()
    conn.close()
    if not loan:
        flash(_("Demande introuvable."),"danger")
        return redirect(url_for('dashboard'))
    return render_template("confirmation.html", loan=loan)

@app.route('/admin/loan/<int:loan_id>/<string:status>')
def admin_change_status(loan_id, status):
    if 'role' not in session or session.get('role') != 'admin':
        flash("Accès refusé.", "danger")
        return redirect(url_for('login'))
    if status not in ('approved', 'rejected'):
        flash("Statut invalide.", "danger")
        return redirect(url_for("admin_dashboard"))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE loans SET status=? WHERE id=?", (status, loan_id))
    conn.commit()

    row = conn.execute("SELECT * FROM loans WHERE id=?", (loan_id,)).fetchone()
    loan = ensure_loan_dict(row)

    if status == 'approved':
        # génère le contrat et met à jour la DB (champ contract_file optionnel)
        contract_path = generate_contract_pdf(loan)
        try:
            cur.execute("ALTER TABLE loans ADD COLUMN contract_file TEXT")
        except Exception:
            # ignore si colonne existe déjà
            pass
        cur.execute("UPDATE loans SET contract_file=? WHERE id=?", (os.path.basename(contract_path), loan_id))
        conn.commit()

        # envoi email avec pièce jointe
        ok = send_loan_approval_email(loan.get("email"), loan, contract_path)
        if ok:
            flash("Demande approuvée et email envoyé.", "success")
        else:
            flash("Demande approuvée — échec envoi email (voir logs).", "warning")
    else:
        flash("Demande rejetée.", "info")

    conn.close()
    return redirect(url_for("admin_dashboard"))
# --- ROUTE POUR LE CLIENT POUR TÉLÉCHARGER SON CONTRAT ---
@app.route('/download/contract/<int:loan_id>')
def download_contract(loan_id):
    if 'role' not in session or session['role'] != 'user':
        return redirect(url_for('login'))

    conn = get_db_connection()
    loan = conn.execute("SELECT * FROM loans WHERE id=? AND user_id=?", 
                        (loan_id, session['user_id'])).fetchone()
    conn.close()

    if not loan or not loan['contract_file']:
        flash(_("Contrat introuvable."), "danger")
        return redirect(url_for('dashboard'))

    return send_from_directory(
        app.config['UPLOAD_FOLDER'],
        loan['contract_file'],
        as_attachment=True
    )

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'],filename, as_attachment=True)

@app.route('/admin')
def admin_dashboard():
    if 'role' not in session or session['role'] != 'admin':
        flash(_("Accès refusé"), "danger")
        return redirect(url_for('login'))

    conn = get_db_connection()
    loans = conn.execute("SELECT * FROM loans").fetchall()
    conn.close()
    return render_template("admin.html", loans=loans)
# --- CREATE TABLES IF NOT EXIST ---
def init_db():
    conn = get_db_connection()
    conn.execute("""CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE,
                        email TEXT UNIQUE,
                        password TEXT,
                        role TEXT
                    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS loans (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        fullname TEXT,
                        dob TEXT,
                        address TEXT,
                        email TEXT,
                        amount REAL,
                        duration INTEGER,
                        period TEXT,
                        objective TEXT,
                        rib TEXT,
                        identity_file TEXT,
                        fee REAL,
                        interest REAL,
                        total REAL,
                        status TEXT,
                        FOREIGN KEY(user_id) REFERENCES users(id)
                    )""")
    conn.commit()
    conn.close()

if __name__ == "__main__":
    import os

    # Crée le dossier de uploads si nécessaire
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Initialise la base de données
    init_db()

    # Détecte le port Render, sinon 5000 par défaut
    port = int(os.environ.get("PORT", 5000))

    # Lance l'app
    app.run(host="0.0.0.0", port=port, debug=True)
