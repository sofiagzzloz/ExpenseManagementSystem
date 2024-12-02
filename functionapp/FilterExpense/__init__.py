import logging
import azure.functions as func
import pymysql
import json
import decimal
import datetime
from shared.dead_letter_queue import send_to_dead_letter_queue  # DLQ helper import

# Database configuration
db_config = {
    "host": "iestlab0001.westeurope.cloudapp.azure.com",
    "user": "CC_A_2",
    "password": "HzbbpLgNtn9jYYVqtzimH1tdtcr0U0SY3v-rPy-slbQ",
    "database": "CC_A_2"
}

# Define response headers
headers = {
    "Content-type": "application/json",
    "Access-Control-Allow-Origin": "*"
}

def filter_expenses_by_category(category_id):
    '''
    Retrieve filtered expense records from the Expenses table by category.
    '''
    try:
        # Establish the database connection
        connection = pymysql.connect(**db_config)
        cursor = connection.cursor(pymysql.cursors.DictCursor)

        # Build the query to filter by category
        query = "SELECT * FROM Expenses WHERE categoryId = %s"
        params = (category_id,)

        # Execute the query
        cursor.execute(query, params)
        result = cursor.fetchall()

        return result

    except pymysql.MySQLError as db_error:
        # Log the error to the Dead Letter Queue
        logging.error(f"MySQL error: {str(db_error)}")
        send_to_dead_letter_queue({
            "error": str(db_error),
            "parameters": {"categoryId": category_id},
            "timestamp": datetime.datetime.utcnow().isoformat()
        })
        raise db_error

    finally:
        # Close the database connection
        if 'cursor' in locals() and cursor:
            cursor.close()
        if 'connection' in locals() and connection:
            connection.close()

def custom_json_serializer(obj):
    """
    Helper function to serialize Decimal, datetime, and date objects.
    """
    if isinstance(obj, decimal.Decimal):
        return float(obj)  # Convert Decimal to float
    elif isinstance(obj, datetime.datetime):
        return obj.isoformat()  # Convert datetime to ISO format string
    elif isinstance(obj, datetime.date):
        return obj.isoformat()  # Convert date to ISO format string
    raise TypeError("Type not serializable")

def serialize_expenses(expenses):
    """
    Manually serialize the fields that may not be serializable (e.g., Decimal, datetime, date).
    """
    serialized_expenses = []
    
    for expense in expenses:
        serialized_expense = {}
        for key, value in expense.items():
            if isinstance(value, decimal.Decimal):
                serialized_expense[key] = float(value)  # Convert Decimal to float
            elif isinstance(value, datetime.datetime) or isinstance(value, datetime.date):
                serialized_expense[key] = value.isoformat()  # Convert datetime or date to ISO format string
            else:
                serialized_expense[key] = value  # Leave other values as is
        serialized_expenses.append(serialized_expense)
    
    return serialized_expenses

def main(req: func.HttpRequest) -> func.HttpResponse:
    '''
    This is the entry point for HTTP calls to the Filter Expenses function.
    '''
    logging.info('Python HTTP trigger function processed a request.')

    # Extract the categoryId from the query string
    category_id = req.params.get('categoryId')

    # If categoryId is missing, log to DLQ and return an error response
    if not category_id:
        error_message = "Missing required field: categoryId"
        logging.error(error_message)
        send_to_dead_letter_queue({
            "error": error_message,
            "parameters": {"categoryId": category_id},
            "timestamp": datetime.datetime.utcnow().isoformat()
        })
        return func.HttpResponse(
            json.dumps({"error": error_message}),
            status_code=400,
            headers=headers
        )

    try:
        # Call the function to filter expenses by category
        expenses = filter_expenses_by_category(category_id)

        # Log the fetched result for debugging purposes
        logging.info(f"Fetched expenses: {expenses}")

        # Serialize the result using custom serializer for Decimal, datetime, and date
        if expenses:
            # Manually serialize the expenses before returning the response
            serialized_expenses = serialize_expenses(expenses)
            return func.HttpResponse(
                json.dumps({"expenses": serialized_expenses}),
                status_code=200,
                headers=headers
            )
        else:
            return func.HttpResponse(
                json.dumps({"message": "No expenses found for the given category"}),
                status_code=404,
                headers=headers
            )
    except Exception as e:
        # Log unexpected errors to the DLQ
        send_to_dead_letter_queue({
            "error": str(e),
            "parameters": {"categoryId": category_id},
            "timestamp": datetime.datetime.utcnow().isoformat()
        })
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            headers=headers
        )