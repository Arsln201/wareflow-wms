from werkzeug.security import check_password_hash
import qrcode
import os

from flask import Flask, render_template, request, redirect, session
from models import db, Product, Employee
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

with app.app_context():
    db.create_all()


# ==========================
# LOGIN
# ==========================

@app.route("/")
def login():

    if "employee_id" in session:
        return redirect("/dashboard")

    return render_template("login.html")


@app.route("/login", methods=["POST"])
def process_login():

    employee_id = request.form.get("employee_id")
    password = request.form.get("password")

    employee = Employee.query.filter_by(employee_id=employee_id).first()

    if employee and check_password_hash(employee.password, password):

        session["employee_id"] = employee.employee_id
        session["employee_name"] = employee.name
        session["role"] = employee.role

        return redirect("/dashboard")

    return render_template(
        "login.html",
        error="Invalid Employee ID or Password"
    )


# ==========================
# LOGOUT
# ==========================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


# ==========================
# DASHBOARD
# ==========================

@app.route("/dashboard")
def dashboard():

    if "employee_id" not in session:
        return redirect("/")

    # Total Products
    total_products = Product.query.count()

    # Total Unique Warehouse Locations
    total_locations = db.session.query(
        Product.rack,
        Product.shelf,
        Product.bin
    ).distinct().count()

    # Total Employees
    total_employees = Employee.query.count()

    # Recently added products
    recent_products = Product.query.order_by(
        Product.id.desc()
    ).limit(5).all()

    return render_template(
        "dashboard.html",
        employee=session["employee_name"],
        role=session["role"],
        total_products=total_products,
        total_locations=total_locations,
        total_employees=total_employees,
        recent_products=recent_products
    )


# ==========================
# INVENTORY
# ==========================

@app.route("/inventory")
def inventory():

    if "employee_id" not in session:
        return redirect("/")

    products = Product.query.order_by(Product.product_name).all()

    return render_template(
        "inventory.html",
        products=products
    )


# ==========================
# ADD PRODUCT
# ==========================

@app.route("/add-product", methods=["GET", "POST"])
def add_product():

    if "employee_id" not in session:
        return redirect("/")

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


# ==========================
# EDIT PRODUCT
# ==========================

@app.route("/edit-product/<int:id>", methods=["GET", "POST"])
def edit_product(id):

    if "employee_id" not in session:
        return redirect("/")

    product = Product.query.get_or_404(id)

    if request.method == "POST":

        product.product_name = request.form["product_name"]
        product.sku = request.form["sku"]
        product.rack = request.form["rack"].upper()
        product.shelf = request.form["shelf"]
        product.bin = request.form["bin"].upper()

        db.session.commit()

        return redirect("/inventory")

    return render_template(
        "edit_product.html",
        product=product
    )


# ==========================
# DELETE PRODUCT
# ==========================

@app.route("/delete-product/<int:id>")
def delete_product(id):

    if "employee_id" not in session:
        return redirect("/")

    product = Product.query.get_or_404(id)

    db.session.delete(product)
    db.session.commit()

    return redirect("/inventory")


# ==========================
# SEARCH PAGE
# ==========================

@app.route("/search")
def search():

    if "employee_id" not in session:
        return redirect("/")

    return render_template("search.html")


# ==========================
# SEARCH RESULT + QR
# ==========================

@app.route("/result", methods=["POST"])
def result():

    if "employee_id" not in session:
        return redirect("/")

    location = request.form.get("location").upper()

    try:
        rack, shelf, bin = location.split("-")

    except ValueError:

        return """
        <h1>❌ Invalid Location Format</h1>
        <br>
        <a href="/search">
            <button>Try Again</button>
        </a>
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


# ==========================
# DEBUG SESSION
# ==========================

@app.route("/test-session")
def test_session():

    return {
        "employee_id": session.get("employee_id"),
        "employee_name": session.get("employee_name"),
        "role": session.get("role")
    }


# ==========================
# START APP
# ==========================

if __name__ == "__main__":
    print("Starting Flask...")
    app.run(debug=True)