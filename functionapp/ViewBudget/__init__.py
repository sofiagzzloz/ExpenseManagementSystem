import logging
import azure.functions as func
import pymysql
import json
import decimal
import datetime  # Ensure datetime is imported
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

def view_budget(user_id, category_id):
    '''
    Retrieve the budget record for a specific user and category.
    '''
    try:
        # Establish the database connection
        connection = pymysql.connect(**db_config)
        cursor = connection.cursor(pymysql.cursors.DictCursor)

        # Query to fetch the budget
        query = """
        SELECT * FROM Budgets WHERE userId = %s AND categoryId = %s
        """
        params = (user_id, category_id)

        # Execute the query
        cursor.execute(query, params)
        result = cursor.fetchone()

        return result

    except pymysql.MySQLError as db_error:
        # Log the error and send to the Dead Letter Queue
        logging.error(f"MySQL error: {str(db_error)}")
        send_to_dead_letter_queue({
            "error": str(db_error),
            "parameters": {"userId": user_id, "categoryId": category_id},
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
    Helper function to serialize Decimal and datetime types.
    """
    if isinstance(obj, decimal.Decimal):
        return float(obj)  # Convert Decimal to float
    elif isinstance(obj, datetime.date):
        return obj.isoformat()  # Convert date or datetime to ISO format string
    raise TypeError(f"Type {type(obj)} not serializable")

def main(req: func.HttpRequest) -> func.HttpResponse:
    '''
    This is the entry point for HTTP calls to the ViewBudget function.
    '''
    logging.info('Python HTTP trigger function processed a request.')

    # Extract userId and categoryId from the query parameters
    user_id = req.params.get('userId')
    category_id = req.params.get('categoryId')

    # Validate the input
    if not user_id or not category_id:
        error_message = "Missing required fields: userId and categoryId"
        logging.error(error_message)
        send_to_dead_letter_queue({
            "error": error_message,
            "parameters": {"userId": user_id, "categoryId": category_id},
            "timestamp": datetime.datetime.utcnow().isoformat()
        })
        return func.HttpResponse(
            json.dumps({"error": error_message}),
            status_code=400,
            headers=headers
        )

    try:
        # Call the function to retrieve the budget
        budget = view_budget(user_id, category_id)

        if budget:
            # Serialize the response using the custom serializer
            return func.HttpResponse(
                json.dumps({"budget": budget}, default=custom_json_serializer),
                status_code=200,
                headers=headers
            )
        else:
            # Return a 404 if no budget is found
            return func.HttpResponse(
                json.dumps({"message": "No budget found for the specified user and category."}),
                status_code=404,
                headers=headers
            )
    except Exception as e:
        # Handle unexpected errors and log to the Dead Letter Queue
        logging.error(f"Unexpected error: {str(e)}")
        send_to_dead_letter_queue({
            "error": str(e),
            "parameters": {"userId": user_id, "categoryId": category_id},
            "timestamp": datetime.datetime.utcnow().isoformat()
        })
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            headers=headers
        )
