from werkzeug.security import check_password_hash
import qrcode
import os

from flask import Flask, render_template, request, redirect, session
from models import db, Product, Employee, StockMovement
from config import Config
from datetime import datetime
from zoneinfo import ZoneInfo
import csv
import io

def format_ist(dt):
    if not dt:
        return "-"

    utc_time = dt.replace(tzinfo=ZoneInfo("UTC"))

    ist_time = utc_time.astimezone(
        ZoneInfo("Asia/Kolkata")
    )

    return ist_time.strftime(
        "%d %b %Y, %I:%M:%S %p"
    )

app = Flask(__name__)
app.config.from_object(Config)
app.jinja_env.globals.update(
    format_ist=format_ist
)

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

    total_employees = Employee.query.count()

    recent_products = Product.query.order_by(
        Product.created_at.desc()
    ).limit(5).all()

    recent_movements = StockMovement.query.order_by(
        StockMovement.created_at.desc()
    ).limit(5).all()

    receive_units = db.session.query(
        db.func.coalesce(
            db.func.sum(StockMovement.quantity),
            0
        )
    ).filter(
        StockMovement.movement_type == "RECEIVE"
    ).scalar()

    issue_units = db.session.query(
        db.func.coalesce(
            db.func.sum(StockMovement.quantity),
            0
        )
    ).filter(
        StockMovement.movement_type == "ISSUE"
    ).scalar()

    move_units = db.session.query(
        db.func.coalesce(
            db.func.sum(StockMovement.quantity),
            0
        )
    ).filter(
        StockMovement.movement_type == "MOVE"
    ).scalar()

    movement_total = StockMovement.query.count()

    if total_products == 0:
        inventory_health = 100
    else:
        inventory_health = round(
            ((total_products - out_of_stock) / total_products) * 100
        )

    return render_template(
        "dashboard.html",
        employee=session["employee_name"],
        role=session["role"],
        total_products=total_products,
        total_locations=total_locations,
        total_units=total_units,
        low_stock=low_stock,
        out_of_stock=out_of_stock,
        total_employees=total_employees,
        recent_products=recent_products,
        recent_movements=recent_movements,
        receive_units=receive_units,
        issue_units=issue_units,
        move_units=move_units,
        movement_total=movement_total,
        inventory_health=inventory_health,
        format_ist=format_ist
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
# STOCK OPERATION
# ==========================


@app.route("/stock-operations")
def stock_operations():

    if "employee_id" not in session:
        return redirect("/")

    products = Product.query.order_by(
        Product.product_name.asc()
    ).all()

    recent_movements = StockMovement.query.order_by(
        StockMovement.created_at.desc()
    ).limit(20).all()

    movement_times = {
        movement.id: format_ist(movement.created_at)
        for movement in recent_movements
    }

    return render_template(
        "stock_operations.html",
        products=products,
        recent_movements=recent_movements,
        movement_times=movement_times
    )


@app.route("/receive-stock", methods=["GET", "POST"])
def receive_stock():

    if "employee_id" not in session:
        return redirect("/")

    employee = Employee.query.filter_by(
        employee_id=session["employee_id"]
    ).first()

    if not employee:
        session.clear()
        return redirect("/")

    products = Product.query.order_by(
        Product.product_name.asc()
    ).all()

    if request.method == "POST":

        product_id = request.form.get("product_id")
        quantity = request.form.get("quantity")
        reason = request.form.get("reason", "").strip()

        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            return render_template(
                "receive_stock.html",
                products=products,
                error="Quantity must be a valid number."
            )

        if quantity <= 0:
            return render_template(
                "receive_stock.html",
                products=products,
                error="Quantity must be greater than zero."
            )

        product = Product.query.get(product_id)

        if not product:
            return render_template(
                "receive_stock.html",
                products=products,
                error="Product not found."
            )

        product.quantity += quantity

        movement = StockMovement(
            product_id=product.id,
            employee_id=employee.id,
            movement_type="RECEIVE",
            quantity=quantity,
            from_location=None,
            to_location=(
                f"{product.rack}-"
                f"{product.shelf}-"
                f"{product.bin}"
            ),
            reason=reason or "Stock received"
        )

        db.session.add(movement)
        db.session.commit()

        return redirect("/stock-operations")

    return render_template(
        "receive_stock.html",
        products=products
    )


@app.route("/issue-stock", methods=["GET", "POST"])
def issue_stock():

    if "employee_id" not in session:
        return redirect("/")

    employee = Employee.query.filter_by(
        employee_id=session["employee_id"]
    ).first()

    if not employee:
        session.clear()
        return redirect("/")

    products = Product.query.order_by(
        Product.product_name.asc()
    ).all()

    if request.method == "POST":

        product_id = request.form.get("product_id")
        quantity = request.form.get("quantity")
        reason = request.form.get("reason", "").strip()

        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            return render_template(
                "issue_stock.html",
                products=products,
                error="Quantity must be a valid number."
            )

        if quantity <= 0:
            return render_template(
                "issue_stock.html",
                products=products,
                error="Quantity must be greater than zero."
            )

        product = Product.query.get(product_id)

        if not product:
            return render_template(
                "issue_stock.html",
                products=products,
                error="Product not found."
            )

        if quantity > product.quantity:
            return render_template(
                "issue_stock.html",
                products=products,
                error="Insufficient stock available."
            )

        product.quantity -= quantity

        movement = StockMovement(
            product_id=product.id,
            employee_id=employee.id,
            movement_type="ISSUE",
            quantity=quantity,
            from_location=(
                f"{product.rack}-"
                f"{product.shelf}-"
                f"{product.bin}"
            ),
            to_location=None,
            reason=reason or "Stock issued"
        )

        db.session.add(movement)
        db.session.commit()

        return redirect("/stock-operations")

    return render_template(
        "issue_stock.html",
        products=products
    )


@app.route("/move-stock", methods=["GET", "POST"])
def move_stock():

    if "employee_id" not in session:
        return redirect("/")

    employee = Employee.query.filter_by(
        employee_id=session["employee_id"]
    ).first()

    if not employee:
        session.clear()
        return redirect("/")

    products = Product.query.order_by(
        Product.product_name.asc()
    ).all()

    if request.method == "POST":

        product_id = request.form.get("product_id")
        quantity = request.form.get("quantity")

        to_rack = request.form.get(
            "to_rack",
            ""
        ).strip().upper()

        to_shelf = request.form.get(
            "to_shelf",
            ""
        ).strip()

        to_bin = request.form.get(
            "to_bin",
            ""
        ).strip().upper()

        reason = request.form.get(
            "reason",
            ""
        ).strip()

        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            return render_template(
                "move_stock.html",
                products=products,
                error="Quantity must be a valid number."
            )

        if quantity <= 0:
            return render_template(
                "move_stock.html",
                products=products,
                error="Quantity must be greater than zero."
            )

        if not to_rack or not to_shelf or not to_bin:
            return render_template(
                "move_stock.html",
                products=products,
                error="Destination location is required."
            )

        product = Product.query.get(product_id)

        if not product:
            return render_template(
                "move_stock.html",
                products=products,
                error="Product not found."
            )

        if quantity > product.quantity:
            return render_template(
                "move_stock.html",
                products=products,
                error="Insufficient stock available."
            )

        from_location = (
            f"{product.rack}-"
            f"{product.shelf}-"
            f"{product.bin}"
        )

        to_location = (
            f"{to_rack}-"
            f"{to_shelf}-"
            f"{to_bin}"
        )

        movement = StockMovement(
            product_id=product.id,
            employee_id=employee.id,
            movement_type="MOVE",
            quantity=quantity,
            from_location=from_location,
            to_location=to_location,
            reason=reason or "Stock moved"
        )

        db.session.add(movement)

        product.rack = to_rack
        product.shelf = to_shelf
        product.bin = to_bin

        db.session.commit()

        return redirect("/stock-operations")

    return render_template(
        "move_stock.html",
        products=products
    )
    
# ==========================
# REPORTS
# ==========================

def parse_report_date(value, end_of_day=False):
    if not value:
        return None

    try:
        parsed = datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return None

    if end_of_day:
        parsed = parsed.replace(
            hour=23,
            minute=59,
            second=59,
            microsecond=999999
        )

    ist_time = parsed.replace(
        tzinfo=ZoneInfo("Asia/Kolkata")
    )

    utc_time = ist_time.astimezone(
        ZoneInfo("UTC")
    )

    return utc_time.replace(tzinfo=None)


def get_report_query():

    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()
    movement_type = request.args.get("movement_type", "").strip().upper()
    employee_id = request.args.get("employee_id", "").strip()
    product_id = request.args.get("product_id", "").strip()

    query = StockMovement.query

    start_date = parse_report_date(date_from)
    end_date = parse_report_date(date_to, end_of_day=True)

    if start_date:
        query = query.filter(
            StockMovement.created_at >= start_date
        )

    if end_date:
        query = query.filter(
            StockMovement.created_at <= end_date
        )

    if movement_type in {"RECEIVE", "ISSUE", "MOVE"}:
        query = query.filter(
            StockMovement.movement_type == movement_type
        )

    if employee_id:
        query = query.filter(
            StockMovement.employee_id == employee_id
        )

    if product_id:
        query = query.filter(
            StockMovement.product_id == product_id
        )

    return (
        query.order_by(
            StockMovement.created_at.desc()
        ),
        date_from,
        date_to,
        movement_type,
        employee_id,
        product_id
    )


@app.route("/reports")
def reports():

    if "employee_id" not in session:
        return redirect("/")

    # -----------------------------------------
    # Filters
    # -----------------------------------------

    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()
    movement_type = request.args.get(
        "movement_type",
        ""
    ).strip().upper()

    employee_id = request.args.get(
        "employee_id",
        ""
    ).strip()

    product_id = request.args.get(
        "product_id",
        ""
    ).strip()

    # -----------------------------------------
    # Base movement query
    # -----------------------------------------

    query = StockMovement.query

    # -----------------------------------------
    # Movement type filter
    # -----------------------------------------

    if movement_type in [
        "RECEIVE",
        "ISSUE",
        "MOVE"
    ]:

        query = query.filter(
            StockMovement.movement_type == movement_type
        )

    else:

        movement_type = ""

    # -----------------------------------------
    # Employee filter
    # -----------------------------------------

    if employee_id:

        try:

            employee_id_int = int(employee_id)

            query = query.filter(
                StockMovement.employee_id
                == employee_id_int
            )

        except ValueError:

            employee_id = ""

    # -----------------------------------------
    # Product filter
    # -----------------------------------------

    if product_id:

        try:

            product_id_int = int(product_id)

            query = query.filter(
                StockMovement.product_id
                == product_id_int
            )

        except ValueError:

            product_id = ""

    # -----------------------------------------
    # Date filters
    # -----------------------------------------

    if date_from:

        try:

            start_date = datetime.strptime(
                date_from,
                "%Y-%m-%d"
            )

            query = query.filter(
                StockMovement.created_at >= start_date
            )

        except ValueError:

            date_from = ""

    if date_to:

        try:

            end_date = datetime.strptime(
                date_to,
                "%Y-%m-%d"
            )

            # Include the entire selected end date
            end_date = end_date.replace(
                hour=23,
                minute=59,
                second=59
            )

            query = query.filter(
                StockMovement.created_at <= end_date
            )

        except ValueError:

            date_to = ""

    # -----------------------------------------
    # Get movements
    # -----------------------------------------

    movements = query.order_by(
        StockMovement.created_at.desc()
    ).limit(200).all()

    # -----------------------------------------
    # Employees and products
    # -----------------------------------------

    employees = Employee.query.order_by(
        Employee.name.asc()
    ).all()

    products = Product.query.order_by(
        Product.product_name.asc()
    ).all()

    # -----------------------------------------
    # Movement statistics
    # -----------------------------------------

    total_received = sum(
        m.quantity
        for m in movements
        if m.movement_type == "RECEIVE"
    )

    total_issued = sum(
        m.quantity
        for m in movements
        if m.movement_type == "ISSUE"
    )

    total_moved = sum(
        m.quantity
        for m in movements
        if m.movement_type == "MOVE"
    )

    # -----------------------------------------
    # Inventory statistics
    # -----------------------------------------

    inventory_total = Product.query.count()

    total_units = db.session.query(
        db.func.coalesce(
            db.func.sum(Product.quantity),
            0
        )
    ).scalar()

    low_stock_total = Product.query.filter(
        Product.quantity > 0,
        Product.quantity <= 10
    ).count()

    out_of_stock_total = Product.query.filter(
        Product.quantity <= 0
    ).count()

    # -----------------------------------------
    # Employee activity
    # -----------------------------------------

    employee_activity = {}

    for movement in movements:

        employee = movement.employee

        # Handle missing/orphan employee records
        if employee is None:

            employee_key = (
                f"unknown-{movement.employee_id}"
            )

            if employee_key not in employee_activity:

                employee_activity[employee_key] = {
                    "employee_id": str(
                        movement.employee_id
                    ),
                    "name": "Unknown Employee",
                    "role": "Unknown",
                    "received": 0,
                    "issued": 0,
                    "moved": 0,
                    "total": 0
                }

            row = employee_activity[
                employee_key
            ]

        else:

            if employee.id not in employee_activity:

                employee_activity[employee.id] = {
                    "employee_id": employee.employee_id,
                    "name": employee.name,
                    "role": employee.role,
                    "received": 0,
                    "issued": 0,
                    "moved": 0,
                    "total": 0
                }

            row = employee_activity[
                employee.id
            ]

        if movement.movement_type == "RECEIVE":

            row["received"] += movement.quantity

        elif movement.movement_type == "ISSUE":

            row["issued"] += movement.quantity

        elif movement.movement_type == "MOVE":

            row["moved"] += movement.quantity

        row["total"] += movement.quantity

    # -----------------------------------------
    # Render reports
    # -----------------------------------------

    return render_template(
        "report.html",

        movements=movements,

        employees=employees,

        products=products,

        employee_activity=list(
            employee_activity.values()
        ),

        inventory_total=inventory_total,

        total_units=total_units,

        low_stock_total=low_stock_total,

        out_of_stock_total=out_of_stock_total,

        total_received=total_received,

        total_issued=total_issued,

        total_moved=total_moved,

        movement_total=len(movements),

        selected_date_from=date_from,

        selected_date_to=date_to,

        selected_movement_type=movement_type,

        selected_employee=employee_id,

        selected_product=product_id
    )


@app.route("/reports/export")
def export_report():

    if "employee_id" not in session:
        return redirect("/")

    # Get the same filters used by the Reports page
    query, date_from, date_to, movement_type, employee_id, product_id = (
        get_report_query()
    )

    movements = query.order_by(
        StockMovement.created_at.desc()
    ).all()

    output = io.StringIO()

    writer = csv.writer(output)

    writer.writerow([
        "Date",
        "Movement Type",
        "Product",
        "SKU",
        "Category",
        "Quantity",
        "Employee ID",
        "Employee",
        "From Location",
        "To Location",
        "Reason"
    ])

    for movement in movements:

        # Safely handle missing product
        product = movement.product

        if product:
            product_name = product.product_name
            sku = product.sku
            category = product.category
        else:
            product_name = "Unknown Product"
            sku = "Unknown"
            category = "Unknown"

        # Safely handle missing employee
        employee = movement.employee

        if employee:
            employee_id_value = employee.employee_id
            employee_name = employee.name
        else:
            employee_id_value = "Unknown"
            employee_name = "Unknown Employee"

        writer.writerow([
            format_ist(movement.created_at),
            movement.movement_type,
            product_name,
            sku,
            category,
            movement.quantity,
            employee_id_value,
            employee_name,
            movement.from_location or "",
            movement.to_location or "",
            movement.reason or ""
        ])

    response = app.response_class(
        output.getvalue(),
        mimetype="text/csv"
    )

    response.headers["Content-Disposition"] = (
        "attachment; filename=wareflow-stock-report.csv"
    )

    return response

# ==========================
# PHASE 6 - SCANNER
# ==========================

@app.route("/scanner")
def scanner():

    if "employee_id" not in session:
        return redirect("/")

    return render_template("scanner.html")

@app.route("/scanner/result")
def scanner_result():

    if "employee_id" not in session:
        return redirect("/")

    scanned_value = request.args.get("value", "").strip()

    if not scanned_value:
        return render_template(
            "scanner.html",
            error="No QR or barcode data was received."
        )

    product = None
    location = None
    scan_type = "UNKNOWN"

    # -----------------------------------------
    # 1. Existing WareFlow location QR
    # Example:
    # http://127.0.0.1:5000/location/A12-04-B
    # -----------------------------------------

    if "/location/" in scanned_value:

        location = scanned_value.split(
            "/location/",
            1
        )[1].strip().upper()

        scan_type = "LOCATION"

    else:

        # -----------------------------------------
        # 2. Direct location code
        # Example:
        # A12-04-B
        # -----------------------------------------

        possible_location = scanned_value.upper()

        parts = possible_location.split("-")

        if len(parts) == 3:

            location = possible_location
            scan_type = "LOCATION"

    # -----------------------------------------
    # 3. Find product by location
    # -----------------------------------------

    if location:

        parts = location.split("-")

        if len(parts) == 3:

            rack = parts[0].strip().upper()
            shelf = parts[1].strip()
            bin_value = parts[2].strip().upper()

            product = Product.query.filter_by(
                rack=rack,
                shelf=shelf,
                bin=bin_value
            ).first()

    # -----------------------------------------
    # 4. If location didn't find product,
    #    try SKU
    # -----------------------------------------

    if product is None:

        product = Product.query.filter(
            db.func.upper(Product.sku)
            == scanned_value.upper()
        ).first()

        if product:

            scan_type = "PRODUCT"

            location = (
                f"{product.rack}-"
                f"{product.shelf}-"
                f"{product.bin}"
            )

    # -----------------------------------------
    # 5. Product found
    # -----------------------------------------

    if product:

        return render_template(
            "scan_result.html",
            scan_type=scan_type,
            scanned_value=scanned_value,
            location=location,
            product=product
        )

    # -----------------------------------------
    # 6. Nothing found
    # -----------------------------------------

    return render_template(
        "scan_result.html",
        scan_type="UNKNOWN",
        scanned_value=scanned_value,
        location=None,
        product=None
    )


# ==========================
# START APP
# ==========================

if __name__ == "__main__":
    print("Starting Flask...")
    app.run(debug=True)