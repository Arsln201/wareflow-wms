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

    total_products = Product.query.count()

    total_locations = db.session.query(
        Product.rack,
        Product.shelf,
        Product.bin
    ).distinct().count()

    total_units = db.session.query(
        db.func.coalesce(
            db.func.sum(Product.quantity),
            0
        )
    ).scalar()

    low_stock = Product.query.filter(
        Product.quantity.between(1, 10)
    ).count()

    out_of_stock = Product.query.filter(
        Product.quantity <= 0
    ).count()

    return render_template(
        "dashboard.html",
        employee=session["employee_name"],
        role=session["role"],
        total_products=total_products,
        total_locations=total_locations,
        total_units=total_units,
        low_stock=low_stock,
        out_of_stock=out_of_stock
    )


# ==========================
# INVENTORY
# ==========================

@app.route("/inventory")
def inventory():

    if "employee_id" not in session:
        return redirect("/")

    search = request.args.get("search", "").strip()
    category = request.args.get("category", "").strip()
    status = request.args.get("status", "").strip()

    query = Product.query

    if search:
        query = query.filter(
            db.or_(
                Product.product_name.ilike(f"%{search}%"),
                Product.sku.ilike(f"%{search}%"),
                Product.rack.ilike(f"%{search}%"),
                Product.shelf.ilike(f"%{search}%"),
                Product.bin.ilike(f"%{search}%")
            )
        )

    if category:
        query = query.filter_by(category=category)

    if status == "in_stock":
        query = query.filter(Product.quantity > 10)

    elif status == "low_stock":
        query = query.filter(
            Product.quantity.between(1, 10)
        )

    elif status == "out_of_stock":
        query = query.filter(Product.quantity <= 0)

    products = query.order_by(
        Product.product_name.asc()
    ).all()

    categories = db.session.query(
        Product.category
    ).distinct().order_by(
        Product.category.asc()
    ).all()

    total_products = Product.query.count()

    total_units = db.session.query(
        db.func.coalesce(
            db.func.sum(Product.quantity),
            0
        )
    ).scalar()

    low_stock = Product.query.filter(
        Product.quantity.between(1, 10)
    ).count()

    out_of_stock = Product.query.filter(
        Product.quantity <= 0
    ).count()

    return render_template(
        "inventory.html",
        products=products,
        categories=[row[0] for row in categories],
        total_products=total_products,
        total_units=total_units,
        low_stock=low_stock,
        out_of_stock=out_of_stock,
        search=search,
        selected_category=category,
        selected_status=status
    )


# ==========================
# ADD PRODUCT
# ==========================

@app.route("/add-product", methods=["GET", "POST"])
def add_product():

    if "employee_id" not in session:
        return redirect("/")

    if request.method == "POST":

        product_name = request.form.get("product_name", "").strip()
        sku = request.form.get("sku", "").strip().upper()
        category = request.form.get("category", "").strip()
        supplier = request.form.get("supplier", "").strip()
        rack = request.form.get("rack", "").strip().upper()
        shelf = request.form.get("shelf", "").strip()
        bin_value = request.form.get("bin", "").strip().upper()

        try:
            quantity = int(request.form.get("quantity", 0))
        except ValueError:
            return render_template(
                "add_product.html",
                error="Quantity must be a valid number."
            )

        if quantity < 0:
            return render_template(
                "add_product.html",
                error="Quantity cannot be negative."
            )

        existing_product = Product.query.filter_by(
            sku=sku
        ).first()

        if existing_product:
            return render_template(
                "add_product.html",
                error="SKU already exists."
            )

        product = Product(
            product_name=product_name,
            sku=sku,
            category=category or "General",
            quantity=quantity,
            supplier=supplier or "Unknown",
            rack=rack,
            shelf=shelf,
            bin=bin_value
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

        product_name = request.form.get(
            "product_name",
            ""
        ).strip()

        sku = request.form.get(
            "sku",
            ""
        ).strip().upper()

        category = request.form.get(
            "category",
            ""
        ).strip()

        supplier = request.form.get(
            "supplier",
            ""
        ).strip()

        rack = request.form.get(
            "rack",
            ""
        ).strip().upper()

        shelf = request.form.get(
            "shelf",
            ""
        ).strip()

        bin_value = request.form.get(
            "bin",
            ""
        ).strip().upper()

        try:
            quantity = int(
                request.form.get("quantity", 0)
            )
        except ValueError:
            return render_template(
                "edit_product.html",
                product=product,
                error="Quantity must be a valid number."
            )

        if quantity < 0:
            return render_template(
                "edit_product.html",
                product=product,
                error="Quantity cannot be negative."
            )

        duplicate_sku = Product.query.filter(
            Product.sku == sku,
            Product.id != product.id
        ).first()

        if duplicate_sku:
            return render_template(
                "edit_product.html",
                product=product,
                error="SKU already exists."
            )

        product.product_name = product_name
        product.sku = sku
        product.category = category or "General"
        product.quantity = quantity
        product.supplier = supplier or "Unknown"
        product.rack = rack
        product.shelf = shelf
        product.bin = bin_value

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


@app.route("/qr-management")
def qr_management():

    if "employee_id" not in session:
        return redirect("/")

    products = Product.query.order_by(
        Product.rack,
        Product.shelf,
        Product.bin
    ).all()

    return render_template(
        "qr_management.html",
        products=products
    )


# ==========================
# SEARCH RESULT + QR
# ==========================

@app.route("/location/<path:location>")
def warehouse_location(location):

    if "employee_id" not in session:
        return redirect("/")

    location = location.strip().upper()

    parts = location.split("-")

    if len(parts) != 3:
        return render_template(
            "location_not_found.html",
            location=location
        )

    rack, shelf, bin_value = parts

    product = Product.query.filter_by(
        rack=rack,
        shelf=shelf,
        bin=bin_value
    ).first()

    if not product:
        return render_template(
            "location_not_found.html",
            location=location
        )

    return render_template(
        "location.html",
        product=product,
        location=location
    )


@app.route("/result", methods=["POST"])
def result():

    if "employee_id" not in session:
        return redirect("/")

    location = request.form.get("location", "").strip().upper()

    if not location:
        return render_template(
            "search.html",
            error="Please enter a warehouse location."
        )

    parts = location.split("-")

    if len(parts) != 3:
        return render_template(
            "search.html",
            error="Invalid location format. Use Rack-Shelf-Bin."
        )

    rack, shelf, bin_value = parts

    rack = rack.strip().upper()
    shelf = shelf.strip()
    bin_value = bin_value.strip().upper()

    if not rack or not shelf or not bin_value:
        return render_template(
            "search.html",
            error="All location fields are required."
        )

    product = Product.query.filter_by(
        rack=rack,
        shelf=shelf,
        bin=bin_value
    ).first()

    if not product:
        return render_template(
            "location_not_found.html",
            location=location
        )

    qr_directory = os.path.join(
        "static",
        "qr"
    )

    os.makedirs(
        qr_directory,
        exist_ok=True
    )

    filename = f"{rack}-{shelf}-{bin_value}.png"

    filepath = os.path.join(
        qr_directory,
        filename
    )

    # URL that the QR code will contain
    qr_url = request.host_url.rstrip("/") + f"/location/{location}"

    # Generate QR code
    img = qrcode.make(qr_url)

    # Save QR image
    img.save(filepath)

    return render_template(
        "qr.html",
        qr_image=f"/static/qr/{filename}",
        location=location,
        product=product
    )


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