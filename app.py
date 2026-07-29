from functools import wraps
from werkzeug.security import check_password_hash, generate_password_hash
import qrcode
import os

from flask import Flask, render_template, request, redirect, session

from models import (
    db,
    Product,
    Employee,
    StockMovement,
    WarehouseAlert
)

from config import Config
from datetime import datetime
from zoneinfo import ZoneInfo
import csv
import io

def role_required(*allowed_roles):
    def decorator(function):

        @wraps(function)
        def wrapper(*args, **kwargs):

            # Not logged in
            if "employee_id" not in session:
                return redirect("/")

            # Get current role
            current_role = session.get("role")

            # Missing/invalid role
            if not current_role:
                session.clear()
                return redirect("/")

            # Role not allowed
            if current_role not in allowed_roles:
                return render_template(
                    "access_denied.html",
                    role=current_role,
                    allowed_roles=allowed_roles
                ), 403

            return function(*args, **kwargs)

        return wrapper

    return decorator

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

def generate_stock_alerts():

    products = Product.query.all()

    for product in products:

        # ==========================================
        # OUT OF STOCK
        # ==========================================

        if product.quantity <= 0:

            # Remove old LOW STOCK alerts
            WarehouseAlert.query.filter_by(
                product_id=product.id,
                alert_type="LOW_STOCK"
            ).delete()

            # Check if an unread OUT OF STOCK alert exists
            existing_alert = WarehouseAlert.query.filter_by(
                product_id=product.id,
                alert_type="OUT_OF_STOCK",
                is_read=False
            ).first()

            if not existing_alert:

                alert = WarehouseAlert(
                    product_id=product.id,
                    alert_type="OUT_OF_STOCK",
                    title="Out of Stock",
                    message=(
                        f"{product.product_name} "
                        f"is currently out of stock."
                    )
                )

                db.session.add(alert)


        # ==========================================
        # LOW STOCK
        # ==========================================

        elif product.quantity <= 10:

            # Remove OUT OF STOCK alerts
            WarehouseAlert.query.filter_by(
                product_id=product.id,
                alert_type="OUT_OF_STOCK"
            ).delete()

            # Check if unread LOW STOCK alert exists
            existing_alert = WarehouseAlert.query.filter_by(
                product_id=product.id,
                alert_type="LOW_STOCK",
                is_read=False
            ).first()

            if not existing_alert:

                alert = WarehouseAlert(
                    product_id=product.id,
                    alert_type="LOW_STOCK",
                    title="Low Stock Warning",
                    message=(
                        f"{product.product_name} has only "
                        f"{product.quantity} units remaining."
                    )
                )

                db.session.add(alert)


        # ==========================================
        # NORMAL STOCK
        # ==========================================

        else:

            # Product has more than 10 units.
            # Remove active stock warnings.
            WarehouseAlert.query.filter(
                WarehouseAlert.product_id == product.id,
                WarehouseAlert.alert_type.in_([
                    "OUT_OF_STOCK",
                    "LOW_STOCK"
                ])
            ).delete(
                synchronize_session=False
            )

    db.session.commit()


# ==========================
# LOGIN
# ==========================

@app.route("/")
def login():

    if "employee_id" in session:
        return redirect("/dashboard")

    login_error = request.args.get("login_error") == "1"

    return render_template(
        "login.html",
        login_failed=login_error,
        error=(
            "Invalid Employee ID or Password"
            if login_error
            else None
        )
    )


@app.route("/login", methods=["POST"])
def process_login():

    employee_id = request.form.get("employee_id", "").strip()
    password = request.form.get("password", "")

    employee = Employee.query.filter_by(
        employee_id=employee_id
    ).first()

    if employee and check_password_hash(
        employee.password,
        password
    ):

        session["employee_id"] = employee.employee_id
        session["employee_name"] = employee.name
        session["role"] = employee.role

        return redirect("/dashboard")

    # IMPORTANT:
    # Don't render login.html directly after failed POST.
    # Redirect instead so browser Back/Refresh won't restore
    # the old invalid-login response.

    return redirect("/?login_error=1")


# ==========================
# LOGOUT
# ==========================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


@app.route("/alerts")
@role_required("Admin", "Manager", "Employee")
def alerts():

    if "employee_id" not in session:
        return redirect("/")

    generate_stock_alerts()

    alert_list = WarehouseAlert.query.order_by(
        WarehouseAlert.created_at.desc()
    ).all()

    unread_count = WarehouseAlert.query.filter_by(
        is_read=False
    ).count()

    return render_template(
        "alerts.html",
        alerts=alert_list,
        unread_count=unread_count
    )

@app.route("/alerts/read/<int:alert_id>")
@role_required("Admin", "Manager", "Employee")
def mark_alert_read(alert_id):

    if "employee_id" not in session:
        return redirect("/")

    alert = WarehouseAlert.query.get_or_404(alert_id)

    alert.is_read = True

    db.session.commit()

    return redirect("/alerts")

@app.route("/alerts/read-all")
@role_required("Admin", "Manager", "Employee")
def mark_all_alerts_read():

    if "employee_id" not in session:
        return redirect("/")

    WarehouseAlert.query.filter_by(
        is_read=False
    ).update(
        {
            WarehouseAlert.is_read: True
        },
        synchronize_session=False
    )

    db.session.commit()

    return redirect("/alerts")

@app.route("/dashboard")
@role_required("Admin", "Manager", "Employee")
def dashboard():

    if "employee_id" not in session:
        return redirect("/")

    # ==========================================
    # BASIC INVENTORY STATISTICS
    # ==========================================

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
    ).scalar() or 0

    low_stock = Product.query.filter(
        Product.quantity.between(1, 10)
    ).count()

    out_of_stock = Product.query.filter(
        Product.quantity <= 0
    ).count()

    total_employees = Employee.query.count()


    # ==========================================
    # RECENT PRODUCTS
    # ==========================================

    recent_products = Product.query.order_by(
        Product.created_at.desc()
    ).limit(5).all()


    # ==========================================
    # RECENT STOCK MOVEMENTS
    # ==========================================

    recent_movements = StockMovement.query.order_by(
        StockMovement.created_at.desc()
    ).limit(5).all()


    # ==========================================
    # MOVEMENT TOTALS
    # ==========================================

    receive_units = db.session.query(
        db.func.coalesce(
            db.func.sum(StockMovement.quantity),
            0
        )
    ).filter(
        StockMovement.movement_type == "RECEIVE"
    ).scalar() or 0


    issue_units = db.session.query(
        db.func.coalesce(
            db.func.sum(StockMovement.quantity),
            0
        )
    ).filter(
        StockMovement.movement_type == "ISSUE"
    ).scalar() or 0


    move_units = db.session.query(
        db.func.coalesce(
            db.func.sum(StockMovement.quantity),
            0
        )
    ).filter(
        StockMovement.movement_type == "MOVE"
    ).scalar() or 0


    movement_total = StockMovement.query.count()


    # ==========================================
    # INVENTORY HEALTH
    # ==========================================

    if total_products == 0:

        inventory_health = 100

    else:

        inventory_health = round(
            (
                (total_products - out_of_stock)
                / total_products
            ) * 100
        )

        inventory_health = max(
            0,
            min(inventory_health, 100)
        )


    # ==========================================
    # STOCK MOVEMENT CHART
    # ==========================================

    max_movement = max(
        receive_units,
        issue_units,
        move_units,
        1
    )


    movement_chart = {

        "receive": receive_units,

        "issue": issue_units,

        "move": move_units,

        "receive_percent": round(
            (receive_units / max_movement) * 100,
            1
        ),

        "issue_percent": round(
            (issue_units / max_movement) * 100,
            1
        ),

        "move_percent": round(
            (move_units / max_movement) * 100,
            1
        )

    }


    # ==========================================
    # RENDER DASHBOARD
    # ==========================================

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

        movement_chart=movement_chart,

        format_ist=format_ist

    )


# ==========================
# INVENTORY
# ==========================

@app.route("/inventory")
@role_required("Admin", "Manager", "Employee")
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

@app.route("/add-product")
@role_required("Admin", "Manager")
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
@role_required("Admin", "Manager")
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

@app.route("/delete-product/<int:id>", methods=["POST"])
@role_required("Admin")
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
@role_required("Admin", "Manager", "Employee")
def search():

    if "employee_id" not in session:
        return redirect("/")

    return render_template("search.html")


@app.route("/qr-management")
@role_required("Admin", "Manager")
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
@role_required("Admin", "Manager", "Employee")
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
@role_required("Admin", "Manager", "Employee")
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
@role_required("Admin", "Manager", "Employee")
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
@role_required("Admin", "Manager", "Employee")
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
@role_required("Admin", "Manager")
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
@role_required("Admin", "Manager")
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
@role_required("Admin", "Manager", "Employee")
def scanner():

    if "employee_id" not in session:
        return redirect("/")

    return render_template("scanner.html")

@app.route("/scanner/result")
@role_required("Admin", "Manager", "Employee")
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
# EMPLOYEE-MANAGEMENT
# ==========================


@app.route("/employee-management")
@role_required("Admin")
def employee_management():

    employees = Employee.query.order_by(
        Employee.name.asc()
    ).all()

    return render_template(
        "employee_management.html",
        employees=employees
    )

@app.route("/employee-management/add", methods=["GET", "POST"])
@role_required("Admin")
def add_employee():

    if request.method == "POST":

        employee_id = request.form.get("employee_id", "").strip().upper()
        name = request.form.get("name", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "").strip()

        # Validate required fields
        if not employee_id or not name or not password or not role:
            return render_template(
                "add_employee.html",
                error="All fields are required."
            )

        # Validate role
        allowed_roles = ["Admin", "Manager", "Employee"]

        if role not in allowed_roles:
            return render_template(
                "add_employee.html",
                error="Invalid role selected."
            )

        # Check duplicate Employee ID
        existing_employee = Employee.query.filter_by(
            employee_id=employee_id
        ).first()

        if existing_employee:
            return render_template(
                "add_employee.html",
                error="Employee ID already exists."
            )

        # Hash password
        hashed_password = generate_password_hash(password)

        employee = Employee(
            employee_id=employee_id,
            name=name,
            password=hashed_password,
            role=role
        )

        db.session.add(employee)
        db.session.commit()

        return redirect("/employee-management")

    return render_template("add_employee.html")

@app.route("/employee-management/edit/<int:employee_id>", methods=["GET", "POST"])
@role_required("Admin")
def edit_employee(employee_id):

    employee = Employee.query.get_or_404(employee_id)

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        role = request.form.get("role", "").strip()
        password = request.form.get("password", "")

        if not name or not role:
            return render_template(
                "edit_employee.html",
                employee=employee,
                error="Name and role are required."
            )

        allowed_roles = ["Admin", "Manager", "Employee"]

        if role not in allowed_roles:
            return render_template(
                "edit_employee.html",
                employee=employee,
                error="Invalid role selected."
            )

        employee.name = name
        employee.role = role

        # Change password only if a new password was entered
        if password.strip():
            employee.password = generate_password_hash(password)

        db.session.commit()

        return redirect("/employee-management")

    return render_template(
        "edit_employee.html",
        employee=employee
    )

@app.route("/employee-management/delete/<int:employee_id>", methods=["POST"])
@role_required("Admin")
def delete_employee(employee_id):

    employee = Employee.query.get_or_404(employee_id)

    # Don't allow deleting yourself
    if employee.employee_id == session.get("employee_id"):
        return redirect("/employee-management")

    # Check whether this employee has stock movement history
    movements = StockMovement.query.filter_by(
        employee_id=employee.id
    ).all()

    if movements:
        return render_template(
            "employee_delete_blocked.html",
            employee=employee,
            movement_count=len(movements)
        ), 409

    db.session.delete(employee)
    db.session.commit()

    return redirect("/employee-management")


# ==========================
# START APP
# ==========================

if __name__ == "__main__":
    print("Starting Flask...")
    app.run(debug=True)