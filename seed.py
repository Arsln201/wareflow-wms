from app import app
from models import db, Employee, Product
from werkzeug.security import generate_password_hash

with app.app_context():

    # ---------- Employee ----------

    if not Employee.query.filter_by(employee_id="EMP1001").first():

        employee = Employee(
            employee_id="EMP1001",
            name="Mirza Arsalan",
            password=generate_password_hash("admin123"),
            role="Admin"
        )

        db.session.add(employee)

    # ---------- Products ----------

    products = [

        Product(
            product_name="Maggi Noodles",
            sku="890105800001",
            rack="A12",
            shelf="04",
            bin="B"
        ),

        Product(
            product_name="Coca Cola",
            sku="890210000111",
            rack="B08",
            shelf="02",
            bin="A"
        ),

        Product(
            product_name="Lay's Chips",
            sku="890149110001",
            rack="C05",
            shelf="01",
            bin="C"
        )

    ]

    for product in products:

        if not Product.query.filter_by(sku=product.sku).first():
            db.session.add(product)

    db.session.commit()

    print("✅ Database seeded successfully!")