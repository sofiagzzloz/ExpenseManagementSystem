import logging
import azure.functions as func
import pymysql
import json
import datetime
from shared.dead_letter_queue import send_to_dead_letter_queue  # Import the DLQ helper function

# Database configuration
db_config = {
    "host": "iestlab0001.westeurope.cloudapp.azure.com",
    "user": "CC_A_2",
    "password": "HzbbpLgNtn9jYYVqtzimH1tdtcr0U0SY3v-rPy-slbQ",
    "database": "CC_A_2"
}

headers = {
    "Content-type": "application/json",
    "Access-Control-Allow-Origin": "*"
}

def add_expense_to_db(user_id, amount, date, description, category_id):
    """
    Handles inserting the expense into the database.
    """
    connection = None
    cursor = None

    try:
        # Connect to the database
        connection = pymysql.connect(**db_config)
        cursor = connection.cursor()

        query = """
            INSERT INTO Expenses (userId, amount, date, description, categoryId)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(query, (user_id, amount, date, description, category_id))
        connection.commit()

        if cursor.rowcount == 1:
            logging.info("Expense added successfully to the database.")
            return True
        else:
            logging.warning("Expense insertion failed in the database.")
            return False

    except pymysql.Error as db_error:
        logging.error(f"Database error: {db_error}")
        raise
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Main function to handle adding expenses, including validation and Dead Letter Queue logging.
    """
    logging.info("Processing AddExpense function.")

    try:
        # Parse request parameters
        req_body = req.get_json()
        user_id = req_body.get('userId')
        amount = req_body.get('amount')
        date = req_body.get('date')
        description = req_body.get('description')
        category_id = req_body.get('categoryId')

        # Validate required fields
        required_fields = ['userId', 'amount', 'date', 'description', 'categoryId']
        missing_fields = [field for field in required_fields if not req_body.get(field)]

        if missing_fields:
            error_message = f"Missing required fields: {', '.join(missing_fields)}"
            logging.error(error_message)

            # Log to Dead Letter Queue
            invalid_request = {
                "error": error_message,
                "requestBody": req_body,
                "timestamp": datetime.datetime.utcnow().isoformat()
            }
            send_to_dead_letter_queue(invalid_request)

            return func.HttpResponse(
                json.dumps({"message": "Invalid request logged to Dead Letter Queue"}),
                status_code=400,
                headers=headers
            )

        # Add expense to the database
        if add_expense_to_db(user_id, amount, date, description, category_id):
            return func.HttpResponse(
                json.dumps({"message": "Expense added successfully"}),
                status_code=200,
                headers=headers
            )
        else:
            raise Exception("Database insertion failed for unknown reasons.")

    except ValueError as ve:
        logging.error(f"JSON parsing error: {ve}")
        invalid_request = {
            "error": "Invalid JSON format",
            "requestBody": None,
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
        send_to_dead_letter_queue(invalid_request)

        return func.HttpResponse(
            json.dumps({"message": "Invalid JSON format logged to Dead Letter Queue"}),
            status_code=400,
            headers=headers
        )

    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        invalid_request = {
            "error": str(e),
            "requestBody": req_body if 'req_body' in locals() else None,
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
        send_to_dead_letter_queue(invalid_request)

        return func.HttpResponse(
            json.dumps({"message": "An error occurred, logged to Dead Letter Queue"}),
            status_code=500,
            headers=headers
        )
