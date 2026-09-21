from flask import Flask, render_template

app = Flask(__name__)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/rules")
def rules():
    return render_template("rules.html")


@app.route("/details")
def details():
    return render_template("details.html")


@app.route("/payment-pending")
def payment_pending():
    return render_template("payment_pending.html")


@app.route("/multiple-guests")
def multiple_guests():
    return render_template("multiple_guests.html")


@app.route("/review")
def review():
    return render_template("review.html")


@app.route("/payment")
def payment():
    return render_template("payment.html")

    
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)