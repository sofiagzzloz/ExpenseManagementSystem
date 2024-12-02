import logging
import pymysql
import azure.functions as func
from azure.storage.blob import BlobServiceClient
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

# Azure Blob Storage configuration
blob_connection_string = "DefaultEndpointsProtocol=https;AccountName=expensemanagement777;AccountKey=20vipKb66lGG3vXuFZCRiBIhpHW+kL7NYXoPiAPobWNDmsm0S+sjQ8AI4L6atUimKH8mS5tNOCMn+AStPzGfEQ==;EndpointSuffix=core.windows.net"
blob_container_name = "receipts"

# Define response headers
headers = {
    "Content-type": "application/json",
    "Access-Control-Allow-Origin": "*"
}

def delete_receipt_from_db(expense_id):
    try:
        # Establish the database connection
        connection = pymysql.connect(**db_config)
        cursor = connection.cursor()

        # Fetch the file URL for the receipt
        cursor.execute("SELECT fileUrl FROM Receipts WHERE expenseId = %s", (expense_id,))
        result = cursor.fetchone()
        if not result:
            error_message = f"No receipt found for Expense ID {expense_id}."
            logging.warning(error_message)
            send_to_dead_letter_queue({
                "error": error_message,
                "parameters": {"expenseId": expense_id},
                "timestamp": datetime.datetime.utcnow().isoformat()
            })
            return False, None

        file_url = result[0]
        file_name = file_url.split("/")[-1]  # Extract the file name from the URL

        # Delete the receipt from the database
        cursor.execute("DELETE FROM Receipts WHERE expenseId = %s", (expense_id,))
        connection.commit()

        logging.info(f"Receipt for Expense ID {expense_id} deleted successfully from database.")
        return True, file_name

    except pymysql.MySQLError as db_error:
        error_message = f"MySQL error: {str(db_error)}"
        logging.error(error_message)
        send_to_dead_letter_queue({
            "error": error_message,
            "parameters": {"expenseId": expense_id},
            "timestamp": datetime.datetime.utcnow().isoformat()
        })
        raise db_error

    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
        if 'connection' in locals() and connection:
            connection.close()

def delete_blob_from_storage(file_name):
    try:
        blob_service_client = BlobServiceClient.from_connection_string(blob_connection_string)
        blob_client = blob_service_client.get_blob_client(container=blob_container_name, blob=file_name)

        # Delete the blob
        blob_client.delete_blob()
        logging.info(f"Blob {file_name} deleted successfully from Azure Blob Storage.")
        return True
    except Exception as e:
        error_message = f"Error deleting blob: {str(e)}"
        logging.error(error_message)
        send_to_dead_letter_queue({
            "error": error_message,
            "parameters": {"fileName": file_name},
            "timestamp": datetime.datetime.utcnow().isoformat()
        })
        return False

def delete_receipt(expense_id):
    # Step 1: Delete receipt from the database
    success, file_name = delete_receipt_from_db(expense_id)
    if not success:
        return {"error": f"No receipt found for Expense ID {expense_id}"}

    # Step 2: Delete the file from Blob Storage
    blob_deleted = delete_blob_from_storage(file_name)
    if not blob_deleted:
        return {"error": f"Failed to delete blob for file: {file_name}"}

    return {"message": "Receipt deleted successfully."}

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Python HTTP trigger function processed a request.")

    try:
        # Parse the request body
        req_body = req.get_json()
        expense_id = req_body.get("expenseId")

        if not expense_id:
            error_message = "Missing required field: expenseId"
            logging.error(error_message)
            send_to_dead_letter_queue({
                "error": error_message,
                "parameters": {},
                "timestamp": datetime.datetime.utcnow().isoformat()
            })
            return func.HttpResponse(
                json.dumps({"error": error_message}),
                status_code=400,
                headers=headers
            )

        # Call delete_receipt to handle the deletion
        result = delete_receipt(expense_id)

        if "error" in result:
            return func.HttpResponse(
                json.dumps(result),
                status_code=400,
                headers=headers
            )

        return func.HttpResponse(
            json.dumps(result),
            status_code=200,
            headers=headers
        )

    except Exception as e:
        error_message = f"Unexpected error: {str(e)}"
        logging.error(error_message)
        send_to_dead_letter_queue({
            "error": error_message,
            "parameters": {"expenseId": req_body.get("expenseId")},
            "timestamp": datetime.datetime.utcnow().isoformat()
        })
        return func.HttpResponse(
            json.dumps({"error": error_message}),
            status_code=500,
            headers=headers
        )