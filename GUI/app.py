from flask import Flask, render_template, request, redirect, url_for, flash
from models import db, Expense, Category, Budget
import os
from config import CATEGORIES

# Initialize Flask app
app = Flask(__name__)

# MySQL Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = (
    'mysql+mysqlconnector://CC_A_2:HzbbpLgNtn9jYYVqtzimH1tdtcr0U0SY3v-rPy-slbQ@'
    'iestlab0001.westeurope.cloudapp.azure.com:3306/CC_A_2'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/receipts'
app.secret_key = 'a3f6b2c3e905f4e7dfc21d8b1234fcde4a65e909bcfc87ad'

# Initialize the database
db.init_app(app)

# Routes

# Home page: List expenses
@app.route('/')
def index():
    from datetime import datetime

    # Get the current month in the format 'YYYY-MM'
    current_month = datetime.now().strftime('%Y-%m')

    # Fetch the current budget for the month
    current_budget = Budget.query.filter_by(month=current_month).first()

    # Calculate the total spent for the current month
    total_spent = db.session.query(db.func.sum(Expense.amount)).filter(
        db.func.date_format(Expense.date, '%Y-%m') == current_month
    ).scalar() or 0  # Default to 0 if no expenses

    # Fetch all expenses for the table
    expenses = Expense.query.all()

    return render_template(
        'index.html',
        expenses=expenses,
        current_budget=current_budget.amount if current_budget else None,
        total_spent=total_spent,
        current_month=current_month
    )

# Add new expense
@app.route('/add', methods=['GET', 'POST'])
def add_expense():
    if request.method == 'POST':
        # Get form data
        amount = request.form['amount']
        category = request.form['category']  # Selected category
        date = request.form['date']
        description = request.form['description']
        receipt = request.files['receipt']

        # Handle receipt upload
        receipt_path = None
        if receipt:
            filename = os.path.join(app.config['UPLOAD_FOLDER'], receipt.filename)
            receipt.save(filename)
            receipt_path = filename

        # Create and save new expense
        new_expense = Expense(amount=amount, category=category, date=date,
                              description=description, receipt_path=receipt_path)

        db.session.add(new_expense)
        db.session.commit()
        flash('Expense added successfully!')
        return redirect(url_for('index'))

    return render_template('add_expense.html', categories=CATEGORIES)

# Edit expense
@app.route('/edit/<int:expense_id>', methods=['GET', 'POST'])
def edit_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)

    if request.method == 'POST':
        # Get form data
        expense.amount = request.form['amount']
        expense.category = request.form['category']  # No tags now
        expense.date = request.form['date']
        expense.description = request.form['description']

        # Handle receipt upload
        receipt = request.files['receipt']
        if receipt:
            filename = os.path.join(app.config['UPLOAD_FOLDER'], receipt.filename)
            receipt.save(filename)
            expense.receipt_path = filename

        db.session.commit()
        flash('Expense updated successfully!')
        return redirect(url_for('index'))

    return render_template('edit_expense.html', expense=expense, categories=CATEGORIES)

# Delete expense
@app.route('/delete/<int:expense_id>', methods=['POST'])
def delete_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    db.session.delete(expense)
    db.session.commit()
    flash('Expense deleted successfully!')
    return redirect(url_for('index'))

@app.route('/set_budget', methods=['GET', 'POST'])
def set_budget():
    if request.method == 'POST':
        month = request.form['month']
        amount = request.form['amount']

        # Check if budget already exists for the month
        budget = Budget.query.filter_by(month=month).first()
        if budget:
            budget.amount = amount  # Update existing budget
        else:
            budget = Budget(month=month, amount=amount)
            db.session.add(budget)
        
        db.session.commit()
        flash(f"Budget for {month} set to {amount} successfully!")
        return redirect(url_for('index'))

    return render_template('set_budget.html')

@app.route('/view_budget/<month>')
def view_budget(month):
    # Example data - replace with actual database queries
    budget = Budget.query.filter_by(month=month).first()
    total_spent = db.session.query(db.func.sum(Expense.amount)).filter(
        db.func.strftime('%Y-%m', Expense.date) == month
    ).scalar() or 0  # Sum of all expenses for the month
    
    return render_template(
        'view_budget.html',
        month=month,
        budget_amount=budget.amount if budget else 0,
        total_spent=total_spent
    )

@app.route('/filter', methods=['GET'])
def filter_expenses():
    selected_category = request.args.get('category')  # Selected category from query string

    if selected_category:
        expenses = Expense.query.filter_by(category=selected_category).all()
    else:
        expenses = Expense.query.all()

    return render_template('filter_expenses.html', expenses=expenses, categories=CATEGORIES, selected_category=selected_category)

if __name__ == '__main__':
    # Create tables on first run
    with app.app_context():
        db.create_all()
    app.run(debug=True)