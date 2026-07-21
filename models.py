from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    employee_id = db.Column(db.String(20), unique=True, nullable=False)

    name = db.Column(db.String(100), nullable=False)

    password = db.Column(db.String(255), nullable=False)

    role = db.Column(db.String(30), nullable=False)

    def __repr__(self):
        return f"<Employee {self.employee_id}>"


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    product_name = db.Column(db.String(100), nullable=False)

    sku = db.Column(db.String(50), unique=True, nullable=False)

    rack = db.Column(db.String(20), nullable=False)

    shelf = db.Column(db.String(20), nullable=False)

    bin = db.Column(db.String(20), nullable=False)

    def __repr__(self):
        return f"<Product {self.product_name}>"