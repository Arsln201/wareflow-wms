from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime


db = SQLAlchemy()


# ============================================================
# EMPLOYEE
# ============================================================

class Employee(UserMixin, db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    employee_id = db.Column(
        db.String(20),
        unique=True,
        nullable=False
    )

    name = db.Column(
        db.String(100),
        nullable=False
    )

    password = db.Column(
        db.String(255),
        nullable=False
    )

    role = db.Column(
        db.String(30),
        nullable=False
    )

    def __repr__(self):
        return f"<Employee {self.employee_id}>"


# ============================================================
# PRODUCT
# ============================================================

class Product(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    product_name = db.Column(
        db.String(100),
        nullable=False
    )

    sku = db.Column(
        db.String(50),
        unique=True,
        nullable=False
    )

    category = db.Column(
        db.String(50),
        nullable=False,
        default="General"
    )

    quantity = db.Column(
        db.Integer,
        nullable=False,
        default=0
    )

    supplier = db.Column(
        db.String(100),
        nullable=False,
        default="Unknown"
    )

    rack = db.Column(
        db.String(20),
        nullable=False
    )

    shelf = db.Column(
        db.String(20),
        nullable=False
    )

    bin = db.Column(
        db.String(20),
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    # --------------------------------------------------------
    # STOCK STATUS
    # --------------------------------------------------------

    @property
    def stock_status(self):

        if self.quantity <= 0:
            return "Out of Stock"

        if self.quantity <= 10:
            return "Low Stock"

        return "In Stock"

    # --------------------------------------------------------
    # STOCK STATUS TYPE
    # --------------------------------------------------------

    @property
    def stock_status_type(self):

        if self.quantity <= 0:
            return "OUT_OF_STOCK"

        if self.quantity <= 10:
            return "LOW_STOCK"

        return "IN_STOCK"

    def __repr__(self):
        return f"<Product {self.product_name}>"


# ============================================================
# STOCK MOVEMENT
# ============================================================

class StockMovement(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    product_id = db.Column(
        db.Integer,
        db.ForeignKey("product.id"),
        nullable=False
    )

    employee_id = db.Column(
        db.Integer,
        db.ForeignKey("employee.id"),
        nullable=False
    )

    movement_type = db.Column(
        db.String(20),
        nullable=False
    )

    quantity = db.Column(
        db.Integer,
        nullable=False
    )

    from_location = db.Column(
        db.String(50),
        nullable=True
    )

    to_location = db.Column(
        db.String(50),
        nullable=True
    )

    reason = db.Column(
        db.String(255),
        nullable=True
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    # --------------------------------------------------------
    # RELATIONSHIPS
    # --------------------------------------------------------

    product = db.relationship(
        "Product",
        backref="stock_movements"
    )

    employee = db.relationship(
        "Employee",
        backref="stock_movements"
    )

    def __repr__(self):
        return (
            f"<StockMovement "
            f"{self.movement_type} "
            f"{self.quantity}>"
        )


# ============================================================
# WAREHOUSE ALERT
# ============================================================

class WarehouseAlert(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    # --------------------------------------------------------
    # PRODUCT
    # --------------------------------------------------------

    product_id = db.Column(
        db.Integer,
        db.ForeignKey("product.id"),
        nullable=True
    )

    # --------------------------------------------------------
    # ALERT TYPE
    # --------------------------------------------------------

    alert_type = db.Column(
        db.String(30),
        nullable=False
    )

    # Examples:
    #
    # LOW_STOCK
    # OUT_OF_STOCK
    # STOCK_RECOVERED
    # SYSTEM
    #
    # --------------------------------------------------------

    title = db.Column(
        db.String(150),
        nullable=False
    )

    message = db.Column(
        db.String(255),
        nullable=False
    )

    # --------------------------------------------------------
    # READ STATUS
    # --------------------------------------------------------

    is_read = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

    # --------------------------------------------------------
    # CREATED TIME
    # --------------------------------------------------------

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    # --------------------------------------------------------
    # RELATIONSHIP
    # --------------------------------------------------------

    product = db.relationship(
        "Product",
        backref="warehouse_alerts"
    )

    # --------------------------------------------------------
    # DISPLAY HELPERS
    # --------------------------------------------------------

    @property
    def severity(self):

        if self.alert_type == "OUT_OF_STOCK":
            return "critical"

        if self.alert_type == "LOW_STOCK":
            return "warning"

        if self.alert_type == "STOCK_RECOVERED":
            return "success"

        return "info"

    @property
    def icon(self):

        if self.alert_type == "OUT_OF_STOCK":
            return "🚨"

        if self.alert_type == "LOW_STOCK":
            return "⚠️"

        if self.alert_type == "STOCK_RECOVERED":
            return "✓"

        return "ℹ️"

    def __repr__(self):
        return (
            f"<WarehouseAlert "
            f"{self.alert_type}>"
        ) 
        
        from datetime import datetime


class ActivityLog(db.Model):

    __tablename__ = "activity_logs"

    id = db.Column(db.Integer, primary_key=True)

    employee_name = db.Column(
        db.String(120),
        nullable=False
    )

    action = db.Column(
        db.String(100),
        nullable=False
    )

    details = db.Column(
        db.Text,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )