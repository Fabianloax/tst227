
from flask import Flask, flash, render_template, request, redirect, url_for, session
import os
import sqlite3
import secrets
import smtplib
import ssl
from html import escape
from email.message import EmailMessage
from email.utils import formataddr

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "local-development-secret")

DATABASE = "prom.db"


class PostgresConnection:
    """Provide the small SQLite-like interface this app uses for Postgres."""

    def __init__(self, connection):
        self.connection = connection

    def execute(self, query, parameters=()):
        cursor = self.connection.cursor()
        cursor.execute(query.replace("?", "%s"), parameters)
        return cursor

    def commit(self):
        self.connection.commit()

    def close(self):
        self.connection.close()


def send_entrance_email(registration):
    """Email an approved guest their saved entrance code through Gmail SMTP."""
    sender_email = os.environ.get("GMAIL_SMTP_USERNAME")
    app_password = os.environ.get("GMAIL_SMTP_APP_PASSWORD")
    sender_name = os.environ.get("GMAIL_SENDER_NAME", "2K27 Prom")

    if not sender_email or not app_password:
        app.logger.warning(
            "Entrance email was not sent: Gmail SMTP environment settings are missing."
        )
        return False

    guest_name = registration["name"]
    entrance_code = registration["entrance_code"]
    registration_code = registration["registration_code"]
    guest_line = (
        f"Guest: {registration['guest_name']}\n"
        if registration["guest_name"]
        else ""
    )
    text_content = (
        f"Hello {guest_name},\n\n"
        "Your 2K27 Prom payment has been approved.\n\n"
        f"Registration code: {registration_code}\n"
        f"Entrance code: {entrance_code}\n"
        f"{guest_line}\n"
        "Please keep this entrance code safe and present it at the entrance."
    )
    html_content = (
        f"<p>Hello {escape(guest_name)},</p>"
        "<p>Your <strong>2K27 Prom</strong> payment has been approved.</p>"
        f"<p><strong>Registration code:</strong> {escape(registration_code)}<br>"
        f"<strong>Entrance code:</strong> {escape(entrance_code)}</p>"
        + (f"<p><strong>Guest:</strong> {escape(registration['guest_name'])}</p>" if registration["guest_name"] else "")
        + "<p>Please keep this entrance code safe and present it at the entrance.</p>"
    )
    message = EmailMessage()
    message["Subject"] = "Your 2K27 Prom entrance code"
    message["From"] = formataddr((sender_name, sender_email))
    message["To"] = formataddr((guest_name, registration["email"]))
    message.set_content(text_content)
    message.add_alternative(html_content, subtype="html")

    try:
        with smtplib.SMTP_SSL(
            "smtp.gmail.com",
            465,
            context=ssl.create_default_context(),
            timeout=10,
        ) as smtp:
            smtp.login(sender_email, app_password)
            smtp.send_message(message)
        return True
    except (smtplib.SMTPException, OSError) as error:
        app.logger.error("Could not send entrance email through Gmail: %s", error)

    return False


# ================================
# DATABASE
# ================================

def get_db():
    database_url = os.environ.get("DATABASE_URL")

    if database_url:
        import psycopg
        from psycopg.rows import dict_row

        return PostgresConnection(
            psycopg.connect(database_url, row_factory=dict_row)
        )

    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    connection = get_db()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS registrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            registration_code TEXT UNIQUE,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT NOT NULL,
            guest_name TEXT,
            amount TEXT,
            payment_status TEXT DEFAULT 'NOT_PAID',
            entrance_code TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
used_at TIMESTAMP
        )
    """)

    connection.commit()
    connection.close()


# Ensure the production database schema exists when Gunicorn imports this app.
init_db()


# ================================
# PAGES
# ================================

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/rules")
def rules():
    return render_template("rules.html")


@app.route("/details")
def details():
    return render_template("details.html")


@app.route("/multiple-guests")
def multiple_guests():
    return render_template("multiple_guests.html")


@app.route("/review")
def review():
    return render_template("review.html")


@app.route("/payment")
def payment():
    registration = request.args.get("registration")

    return render_template(
        "payment.html",
        registration=registration
    )


@app.route("/payment-pending")
def payment_pending():

    registration_code = request.args.get("registration")

    if not registration_code:
        return "Registration ID missing", 400

    connection = get_db()

    registration = connection.execute("""
        SELECT *
        FROM registrations
        WHERE registration_code = ?
    """, (registration_code,)).fetchone()

    connection.close()

    if registration is None:
        return "Registration not found", 404

    return render_template(
        "payment_pending.html",
        registration=registration
    )
@app.route("/status")
def status():

    registration_code = request.args.get("registration")

    if not registration_code:
        return "Registration ID missing", 400

    connection = get_db()

    registration = connection.execute("""
        SELECT *
        FROM registrations
        WHERE registration_code = ?
    """, (registration_code,)).fetchone()

    connection.close()

    if registration is None:
        return "Registration not found", 404

    if registration["payment_status"] == "PAID":

        return redirect(
            url_for(
                "confirmed",
                registration=registration_code
            )
        )

    return render_template(
        "payment_pending.html",
        registration=registration
    )

@app.route("/payment-reported", methods=["POST"])
def payment_reported():

    registration_code = request.form.get("registration")

    if not registration_code:
        return "Registration ID missing", 400

    connection = get_db()

    registration = connection.execute("""
        SELECT *
        FROM registrations
        WHERE registration_code = ?
    """, (registration_code,)).fetchone()

    if registration is None:
        connection.close()
        return "Registration not found", 404

    if registration["payment_status"] == "PAID":
        connection.close()

        return redirect(
            url_for(
                "confirmed",
                registration=registration_code
            )
        )

    connection.execute("""
        UPDATE registrations
        SET payment_status = ?
        WHERE registration_code = ?
    """, (
        "PAYMENT_REPORTED",
        registration_code
    ))

    connection.commit()
    connection.close()

    return redirect(
        url_for(
            "payment_pending",
            registration=registration_code
        )
    )


@app.route("/confirmed")
def confirmed():

    registration_code = request.args.get("registration")

    if not registration_code:
        return "Registration ID missing", 400

    connection = get_db()

    registration = connection.execute("""
        SELECT *
        FROM registrations
        WHERE registration_code = ?
    """, (registration_code,)).fetchone()

    connection.close()

    if registration is None:
        return "Registration not found", 404

    if registration["payment_status"] != "PAID":
        return "Payment has not been approved", 403

    return render_template(
        "confirmed.html",
        registration=registration
    )


# ================================
# REGISTRATION
# ================================

@app.route("/register", methods=["POST"])
def register():

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    phone = request.form.get("phone", "").strip()
    guest_name = request.form.get("guestName", "").strip()

    registration_code = "2K27-" + secrets.token_hex(3).upper()

    connection = get_db()

    connection.execute("""
        INSERT INTO registrations
        (
            registration_code,
            name,
            email,
            phone,
            guest_name,
            amount,
            payment_status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        registration_code,
        name,
        email,
        phone,
        guest_name,
        "PRICE",
        "NOT_PAID"
    ))

    connection.commit()
    connection.close()

    return redirect(
        url_for(
            "payment",
            registration=registration_code
        )
    )

# ================================
# ADMIN LOGIN
# ================================

ADMIN_PASSWORD = "2k27"
STAFF_PASSWORD = "2k27"

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():

    if request.method == "POST":

        password = request.form.get("password", "")

        if password == ADMIN_PASSWORD:

            session["admin_logged_in"] = True

            return redirect(url_for("admin"))

        return render_template(
            "admin_login.html",
            error="Incorrect password."
        )

    return render_template("admin_login.html")


@app.route("/admin/logout")
def admin_logout():

    session.pop("admin_logged_in", None)

    return redirect(url_for("admin_login"))

# ================================
# STAFF LOGIN
# ================================

@app.route("/staff/login", methods=["GET", "POST"])
def staff_login():

    if request.method == "POST":

        password = request.form.get("password", "")

        if password == STAFF_PASSWORD:

            session["staff_logged_in"] = True

            return redirect(url_for("staff"))

        return render_template(
            "staff_login.html",
            error="Incorrect password."
        )

    return render_template("staff_login.html")


@app.route("/staff/logout")
def staff_logout():

    session.pop("staff_logged_in", None)

    return redirect(url_for("staff_login"))

# ================================
# ADMIN
# ================================

@app.route("/admin")
def admin():

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    connection = get_db()

    registrations = connection.execute("""
        SELECT *
        FROM registrations
        ORDER BY created_at DESC
    """).fetchall()

    connection.close()

    return render_template(
        "admin.html",
        registrations=registrations
    )


@app.route("/admin/approve/<registration_code>", methods=["POST"])
def approve_payment(registration_code):

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    connection = get_db()

    registration = connection.execute("""
        SELECT *
        FROM registrations
        WHERE registration_code = ?
    """, (registration_code,)).fetchone()

    if registration is None:
        connection.close()
        return "Registration not found", 404

    entrance_code = "ENT-" + secrets.token_hex(4).upper()

    connection.execute("""
        UPDATE registrations
        SET payment_status = ?,
            entrance_code = ?
        WHERE registration_code = ?
    """, (
        "PAID",
        entrance_code,
        registration_code
    ))

    connection.commit()

    # Reload the saved record so the email always uses the persisted code.
    registration = connection.execute("""
        SELECT *
        FROM registrations
        WHERE registration_code = ?
    """, (registration_code,)).fetchone()
    connection.close()

    if send_entrance_email(registration):
        flash("Payment approved and entrance code emailed to the guest.")
    else:
        flash(
            "Payment approved and entrance code saved, but the email was not sent. "
            "Check the Gmail SMTP environment settings and try approving again."
        )

    # Stay on the admin dashboard after approval
    return redirect(url_for("admin"))

# ================================
# STAFF ENTRANCE CHECKER
# ================================

@app.route("/staff")
def staff():

    if not session.get("staff_logged_in"):
        return redirect(url_for("staff_login"))

    return render_template("staff.html")


@app.route("/staff/check", methods=["POST"])
def staff_check():

    # Make sure staff is logged in
    if not session.get("staff_logged_in"):
        return redirect(url_for("staff_login"))

    # Get code from form
    entrance_code = request.form.get(
        "entrance_code",
        ""
    ).strip().upper()

    print("STAFF CODE ENTERED:", repr(entrance_code))

    # Empty code
    if not entrance_code:
        return render_template(
            "staff.html",
            error="Please enter an entrance code."
        )

    connection = get_db()

    # Find the entrance code
    registration = connection.execute("""
        SELECT *
        FROM registrations
        WHERE UPPER(TRIM(entrance_code)) = ?
    """, (entrance_code,)).fetchone()

    print("DATABASE RESULT:", dict(registration) if registration else None)

    # Code does not exist
    if registration is None:

        connection.close()

        return render_template(
            "staff.html",
            error="INVALID CODE"
        )

    # Payment has not been approved
    if registration["payment_status"] != "PAID":

        connection.close()

        return render_template(
            "staff.html",
            error="PAYMENT NOT APPROVED"
        )

    # Code has already been used
    if registration["used_at"] is not None:

        connection.close()

        return render_template(
            "staff.html",
            error="ALREADY USED",
            registration=registration
        )

    # Mark ticket as used
    connection.execute("""
        UPDATE registrations
        SET used_at = CURRENT_TIMESTAMP
        WHERE registration_code = ?
    """, (
        registration["registration_code"],
    ))

    connection.commit()
    connection.close()

    # Show successful entry
    return render_template(
        "staff.html",
        valid=True,
        registration=registration
    )


# ================================
# STARTUP
# ================================

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=True
    )
