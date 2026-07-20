import qrcode
import os

from flask import Flask, render_template, request, redirect
from models import db
from config import Config
from warehouse_data import WAREHOUSE

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

with app.app_context():
    db.create_all()

@app.route("/")
def login():
    return render_template("login.html")

@app.route("/login", methods=["POST"])
def process_login():

    employee_id = request.form.get("employee_id")
    password = request.form.get("password")

    # Temporary login
    if employee_id == "EMP1001" and password == "admin123":
        return redirect("/dashboard")

    return "Invalid Employee ID or Password"

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@app.route("/search")
def search():
    return render_template("search.html")

@app.route("/result", methods=["POST"])
def result():

    location = request.form.get("location").upper()

    if location in WAREHOUSE:

        item = WAREHOUSE[location]

        # Generate QR Code
        filename = f"{location}.png"
        filepath = os.path.join("static", "qr", filename)

        img = qrcode.make(location)
        img.save(filepath)

        return render_template(
            "qr.html",
            qr_image=f"/static/qr/{filename}",
            location=location
        )

    return """
    <h1>❌ Location Not Found</h1>

    <br>

    <a href="/search">
        <button>Try Again</button>
    </a>
    """

if __name__ == "__main__":
    print("Starting Flask...")
    app.run(debug=False, use_reloader=False)
    