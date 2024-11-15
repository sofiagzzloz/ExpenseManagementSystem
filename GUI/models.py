from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(100), nullable=False)  # Directly store category as string
    date = db.Column(db.Date, nullable=False)
    description = db.Column(db.String(255), nullable=True)
    receipt_path = db.Column(db.String(255), nullable=True)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

class Budget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    month = db.Column(db.String(7), nullable=False)  # Format: YYYY-MM
    amount = db.Column(db.Float, nullable=False)

