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
    