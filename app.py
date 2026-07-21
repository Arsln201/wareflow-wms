import qrcode
import os

from flask import Flask, render_template, request, redirect
from models import db, Product
from config import Config


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

@app.route("/add-product", methods=["GET", "POST"])
def add_product():

    if request.method == "POST":

        product = Product(
            product_name=request.form["product_name"],
            sku=request.form["sku"],
            rack=request.form["rack"].upper(),
            shelf=request.form["shelf"],
            bin=request.form["bin"].upper()
        )

        db.session.add(product)
        db.session.commit()

        return redirect("/inventory")

    return render_template("add_product.html")

@app.route("/inventory")
def inventory():

    products = Product.query.order_by(Product.product_name).all()

    return render_template(
        "inventory.html",
        products=products
    )

@app.route("/search")
def search():
    return render_template("search.html")

@app.route("/result", methods=["POST"])
def result():

    location = request.form.get("location").upper()

    try:
        rack, shelf, bin = location.split("-")
    except ValueError:
        return """
        <h1>❌ Invalid Location Format</h1>
        <br>
        <a href="/search"><button>Try Again</button></a>
        """

    product = Product.query.filter_by(
        rack=rack,
        shelf=shelf,
        bin=bin
    ).first()

    if product:

        filename = f"{location}.png"
        filepath = os.path.join("static", "qr", filename)

        img = qrcode.make(location)
        img.save(filepath)

        return render_template(
            "qr.html",
            qr_image=f"/static/qr/{filename}",
            location=location,
            product=product
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
    