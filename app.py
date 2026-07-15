import os
import json
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user, login_required,
    logout_user, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from utils.ocr_utils import extract_text
from utils.bert_verifier import verify_document
from utils.payslip_parser import parse_payslip
from utils.bank_parser import parse_bank_statement

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "pdf"}

app = Flask(__name__)
app.config["SECRET_KEY"] = "change-this-secret-key-before-deploying"
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'app.db')}"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ---------------------------------------------------------------- AUTH ----
@app.route("/")
def index():
    return redirect(url_for("dashboard") if current_user.is_authenticated else url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        if not username or not email or not password:
            flash("All fields are required.", "error")
            return redirect(url_for("register"))

        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash("Username or email already registered.", "error")
            return redirect(url_for("register"))

        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
        )
        db.session.add(user)
        db.session.commit()
        flash("Account created. Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        identifier = request.form["identifier"].strip()
        password = request.form["password"]

        user = User.query.filter(
            (User.username == identifier) | (User.email == identifier.lower())
        ).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for("dashboard"))

        flash("Invalid username/email or password.", "error")
        return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


# ----------------------------------------------------------- DASHBOARD ----
@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")


# --------------------------------------------------------------- UPLOAD ----
@app.route("/upload/payslip", methods=["POST"])
@login_required
def upload_payslip():
    return handle_upload(doc_type="payslip")


@app.route("/upload/bankstatement", methods=["POST"])
@login_required
def upload_bankstatement():
    return handle_upload(doc_type="bankstatement")


def handle_upload(doc_type):
    file = request.files.get("document")
    if not file or file.filename == "":
        flash("Please choose a file to upload.", "error")
        return redirect(url_for("dashboard"))

    if not allowed_file(file.filename):
        flash("Only JPG, PNG and PDF files are supported.", "error")
        return redirect(url_for("dashboard"))

    filename = secure_filename(f"{current_user.id}_{doc_type}_{file.filename}")
    save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(save_path)

    # 1. OCR - extract raw text from the image/pdf
    text = extract_text(save_path)

    # 2. BERT-based verification - is this text actually a document of this type?
    verification = verify_document(text, expected_type=doc_type)

    if doc_type == "payslip":
        parsed = parse_payslip(text)
        return render_template(
            "payslip_result.html",
            verification=verification,
            parsed=parsed,
            chart_data=json.dumps(parsed["chart_data"]),
            raw_text=text,
        )
    else:
        parsed = parse_bank_statement(text)
        return render_template(
            "bankstatement_result.html",
            verification=verification,
            parsed=parsed,
            chart_data=json.dumps(parsed["chart_data"]),
            raw_text=text,
        )


if __name__ == "__main__":
    os.makedirs(os.path.join(BASE_DIR, "instance"), exist_ok=True)
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    with app.app_context():
        db.create_all()
    app.run(debug=True, host="0.0.0.0", port=5000)
