print("1. Starting seed.py")

from app import app
print("2. Imported app")

from models import db, Employee
print("3. Imported models")

from werkzeug.security import generate_password_hash
print("4. Imported werkzeug")

with app.app_context():
    print("5. Inside app context")

    employee = Employee.query.filter_by(employee_id="EMP1001").first()
    print("6. Database query completed")

    if employee:
        print("⚠ Employee already exists!")
    else:
        new_employee = Employee(
            employee_id="EMP1001",
            name="Mirza Arsalan",
            password=generate_password_hash("admin123"),
            role="Admin"
        )

        db.session.add(new_employee)
        db.session.commit()

        print("✅ Employee created successfully!")