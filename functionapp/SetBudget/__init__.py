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

def set_budget(user_id, category_id, budget_limit, start_date, end_date):
    '''
    Add or update a budget record in the Budgets table for a unique user/category combination.
    '''
    try:
        # Establish the database connection
        connection = pymysql.connect(**db_config)
        cursor = connection.cursor()

        # Check if a budget already exists for this user and category combination
        cursor.execute("""
            SELECT id FROM Budgets
            WHERE userId = %s AND categoryId = %s
        """, (user_id, category_id))
        existing_budget = cursor.fetchone()

        if existing_budget:
            # If the budget exists, log the message and treat it as a valid situation
            logging.warning(f"Budget already exists for User ID {user_id} and Category ID {category_id}.")
            # Send this specific case to the Dead Letter Queue
            send_to_dead_letter_queue({
                "error": f"Budget already exists for User ID {user_id} and Category ID {category_id}.",
                "parameters": {"userId": user_id, "categoryId": category_id},
                "timestamp": datetime.datetime.utcnow().isoformat()
            })
            return False, "exists"

        # If no budget exists, insert a new record
        cursor.execute("""
            INSERT INTO Budgets (userId, categoryId, budget_limit, start_date, end_date)
            VALUES (%s, %s, %s, %s, %s)
        """, (user_id, category_id, budget_limit, start_date, end_date))
        action = "created"

        # Commit the transaction
        connection.commit()

        # Check if the row was affected
        if cursor.rowcount > 0:
            logging.info(f"Budget {action} successfully: User ID {user_id}, Category ID {category_id}")
            return True, action
        else:
            logging.warning("No rows were affected in the database.")
            return False, None

    except pymysql.MySQLError as db_error:
        # Log and handle MySQL-specific errors
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
    This is the entry point for HTTP calls to the Set Budget function.
    '''
    logging.info('Python HTTP trigger function processed a request.')

    try:
        # Parse the request body
        req_body = req.get_json()

        # Extract parameters from the request
        user_id = req_body.get('userId')
        category_id = req_body.get('categoryId')
        budget_limit = req_body.get('budgetLimit')
        start_date = req_body.get('startDate')
        end_date = req_body.get('endDate')

        # Validate input data
        if not all([user_id, category_id, budget_limit, start_date, end_date]):
            return func.HttpResponse(
                json.dumps({"error": "Missing required fields: userId, categoryId, budgetLimit, startDate, endDate"}),
                status_code=400,
                headers=headers
            )

        # Call the function to set or update the budget
        success, action = set_budget(user_id, category_id, budget_limit, start_date, end_date)
        if success:
            return func.HttpResponse(
                json.dumps({"message": f"Budget {action} successfully."}),
                status_code=200,
                headers=headers
            )
        else:
            if action == "exists":
                return func.HttpResponse(
                    json.dumps({"message": f"Budget already exists for User ID {user_id} and Category ID {category_id}."}),
                    status_code=409,  # Conflict HTTP status code for existing resource
                    headers=headers
                )
            return func.HttpResponse(
                json.dumps({"error": "Failed to set budget"}),
                status_code=500,
                headers=headers
            )

    except Exception as e:
        # Log unexpected errors and send to DLQ
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
