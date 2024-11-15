import logging
import json
import azure.functions as func
from models import db, Expense  # Assuming Expense is already defined in models.py

def view_expenses(req: func.HttpRequest) -> func.HttpResponse:
    try:
        # Fetch all expenses from the database
        expenses = Expense.query.all()

        # Convert expenses into a list of dictionaries
        expenses_list = [
            {
                "id": expense.id,
                "amount": expense.amount,
                "category": expense.category,
                "date": expense.date,
                "description": expense.description,
                "receipt_path": expense.receipt_path
            }
            for expense in expenses
        ]

        # Return expenses as JSON
        return func.HttpResponse(
            json.dumps({"message": "Expenses retrieved successfully", "status": "success", "data": expenses_list}),
            status_code=200,
            mimetype="application/json"
        )
    except Exception as e:
        logging.error(f"Error while fetching expenses: {str(e)}")
        return func.HttpResponse(
            json.dumps({"message": str(e), "status": "error"}),
            status_code=500,
            mimetype="application/json"
        )
