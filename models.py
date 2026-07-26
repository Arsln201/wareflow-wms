from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()


class Employee(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)

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

    @property
    def stock_status(self):
        if self.quantity <= 0:
            return "Out of Stock"

        if self.quantity <= 10:
            return "Low Stock"

        return "In Stock"

    def __repr__(self):
        return f"<Product {self.product_name}>"
    
    
class StockMovement(db.Model):

    id = db.Column(db.Integer, primary_key=True)

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

    product = db.relationship(
        "Product",
        backref="stock_movements"
    )

    employee = db.relationship(
        "Employee",
        backref="stock_movements"
    )

    def __repr__(self):
        return f"<StockMovement {self.movement_type} {self.quantity}>"