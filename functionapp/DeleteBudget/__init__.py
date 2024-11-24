import logging
import azure.functions as func
import pymysql
import json
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

def delete_budget(user_id, category_id):
    '''
    Delete a budget for the specified user and category.
    '''
    try:
        # Establish the database connection
        connection = pymysql.connect(**db_config)
        cursor = connection.cursor()

        # Delete the budget
        query = "DELETE FROM Budgets WHERE userId = %s AND categoryId = %s"
        params = (user_id, category_id)
        cursor.execute(query, params)

        # Commit the transaction
        connection.commit()

        # Check if a row was affected
        if cursor.rowcount > 0:
            logging.info(f"Budget deleted successfully for User ID {user_id}, Category ID {category_id}")
            return True
        else:
            logging.warning(f"No budget found for User ID {user_id}, Category ID {category_id}")
            return False

    except pymysql.MySQLError as db_error:
        # Log error to Dead Letter Queue
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

def main(req: func.HttpRequest) -> func.HttpResponse:
    '''
    This is the entry point for HTTP calls to the DeleteBudget function.
    '''
    logging.info('Python HTTP trigger function processed a request.')

    # Extract parameters from the query string
    user_id = req.params.get('userId')
    category_id = req.params.get('categoryId')

    # Validate input data
    if not all([user_id, category_id]):
        error_message = "Missing required fields: userId, categoryId"
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
        # Call the function to delete the budget
        success = delete_budget(user_id, category_id)
        if success:
            return func.HttpResponse(
                json.dumps({"message": "Budget deleted successfully."}),
                status_code=200,
                headers=headers
            )
        else:
            return func.HttpResponse(
                json.dumps({"error": "No budget found for the given user and category."}),
                status_code=404,
                headers=headers
            )

    except Exception as e:
        # Log unexpected errors to the Dead Letter Queue
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