import os
from flask import Flask, render_template, request, redirect, url_for, session

from utils.ocr_utils import extract_text, parse_salary_slip, parse_bank_statement
from utils.bert_verifier import verify_document
from utils.chart_utils import salary_pie_chart, bank_pie_chart, bank_bar_chart

app = Flask(__name__)
app.secret_key = "change-this-to-a-random-secret-in-production"

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# --- demo credentials only. Replace with a real user store / auth system. ---
VALID_USERS = {
    "admin": "admin123",
    "analyst": "loan@2026",
}


@app.route("/", methods=["GET", "POST"])
def login():
    message, message_type = None, None

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if VALID_USERS.get(username) == password:
            session["user"] = username
            message, message_type = "Login Successfully", "success"
            return render_template("login.html", message=message,
                                    message_type=message_type, redirect_now=True)
        else:
            message = "Login Failed! Invalid Username or Password."
            message_type = "error"

    return render_template("login.html", message=message, message_type=message_type)


@app.route("/upload", methods=["GET", "POST"])
def upload():
    if "user" not in session:
        return redirect(url_for("login"))

    result = None

    if request.method == "POST":
        doc_type = request.form.get("doc_type")
        file = request.files.get("document")

        if not file or file.filename == "":
            result = {"error": "Please choose a file to upload."}
        else:
            save_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
            file.save(save_path)

            # 1. OCR
            ocr_text = extract_text(save_path)

            # 2. BERT verification (is this really the doc type it claims to be?)
            verification = verify_document(ocr_text, doc_type)

            result = {
                "doc_type": doc_type,
                "verification": verification,
                "charts": {},
            }

            # 3. Only build charts once the document is verified
            if verification["verified"]:
                if doc_type == "Salary Slip":
                    fields = parse_salary_slip(ocr_text)
                    result["charts"]["pie"] = salary_pie_chart(fields)
                    result["fields"] = fields
                elif doc_type == "Bank Statement":
                    parsed = parse_bank_statement(ocr_text)
                    result["charts"]["pie"] = bank_pie_chart(
                        parsed["credit_total"], parsed["debit_total"]
                    )
                    result["charts"]["bar"] = bank_bar_chart(parsed["monthly_totals"])
                    result["fields"] = parsed

            os.remove(save_path)  # don't keep uploaded documents on disk

    return render_template("upload.html", result=result, user=session.get("user"))


@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True)
