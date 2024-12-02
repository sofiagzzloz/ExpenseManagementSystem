import logging
import pymysql
import json
import azure.functions as func
import datetime
import uuid
from azure.storage.blob import BlobServiceClient
from shared.dead_letter_queue import send_to_dead_letter_queue  # Import the DLQ helper function

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

# Allowed file types
ALLOWED_FILE_TYPES = ["pdf", "jpg", "jpeg", "png"]

# Azure Blob Storage configuration
blob_connection_string = "DefaultEndpointsProtocol=https;AccountName=expensemanagement777;AccountKey=20vipKb66lGG3vXuFZCRiBIhpHW+kL7NYXoPiAPobWNDmsm0S+sjQ8AI4L6atUimKH8mS5tNOCMn+AStPzGfEQ==;EndpointSuffix=core.windows.net"
blob_container_name = "receipts"

def upload_to_blob(file_name, file_content):
    '''
    Upload a file to Azure Blob Storage with a unique name.
    '''
    try:
        # Generate a unique file name using UUID
        unique_file_name = f"{uuid.uuid4()}_{file_name}"

        blob_service_client = BlobServiceClient.from_connection_string(blob_connection_string)
        blob_client = blob_service_client.get_blob_client(container=blob_container_name, blob=unique_file_name)

        # Upload the file
        blob_client.upload_blob(file_content, overwrite=False)
        logging.info(f"File uploaded successfully: {unique_file_name}")
        return True, f"https://{blob_service_client.account_name}.blob.core.windows.net/{blob_container_name}/{unique_file_name}"
    except Exception as e:
        logging.error(f"Error uploading file to Blob Storage: {str(e)}")
        return False, str(e)

def add_receipt(expense_id, file_name, file_url):
    '''
    Add a new receipt entry to the Receipts table in the database.
    '''
    try:
        # Establish the database connection
        connection = pymysql.connect(**db_config)
        cursor = connection.cursor()

        # Insert a new receipt record
        cursor.execute("""
            INSERT INTO Receipts (expenseId, fileUrl, uploadDate)
            VALUES (%s, %s, %s)
        """, (expense_id, file_url, datetime.datetime.now()))

        # Commit the transaction
        connection.commit()

        if cursor.rowcount > 0:
            logging.info(f"Receipt added successfully for Expense ID {expense_id}")
            return True
        else:
            logging.warning("No rows were affected in the database.")
            return False

    except pymysql.MySQLError as db_error:
        logging.error(f"MySQL error: {str(db_error)}")
        raise db_error

    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
        if 'connection' in locals() and connection:
            connection.close()

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('AddReceipt function processing a request.')

    try:
        # Parse the request
        req_body = req.form
        file = req.files.get('file')  # Get the uploaded file

        expense_id = req_body.get('expenseId')
        if not expense_id:
            return func.HttpResponse(
                json.dumps({"error": "Missing required field: expenseId"}),
                status_code=400,
                headers=headers
            )

        # Validate file
        if not file:
            return func.HttpResponse(
                json.dumps({"error": "No file provided."}),
                status_code=400,
                headers=headers
            )

        file_name = file.filename
        file_extension = file_name.split('.')[-1].lower()

        if file_extension not in ALLOWED_FILE_TYPES:
            error_message = f"Invalid file format: {file_extension}. Allowed formats are {', '.join(ALLOWED_FILE_TYPES)}"
            logging.warning(error_message)

            # Send to Dead Letter Queue
            send_to_dead_letter_queue(json.dumps({
                "error": "Invalid file format",
                "fileName": file_name,
                "expenseId": expense_id,
                "timestamp": str(datetime.datetime.now())
            }))

            return func.HttpResponse(
                json.dumps({"error": error_message}),
                status_code=400,
                headers=headers
            )

        # Upload the file to Blob Storage
        success, blob_url = upload_to_blob(file_name, file.stream.read())
        if not success:
            return func.HttpResponse(
                json.dumps({"error": f"Failed to upload file to Blob Storage: {blob_url}"}),
                status_code=500,
                headers=headers
            )

        # Add receipt to the database
        success = add_receipt(expense_id, file_name, blob_url)
        if success:
            return func.HttpResponse(
                json.dumps({"message": "Receipt uploaded successfully", "fileUrl": blob_url}),
                status_code=200,
                headers=headers
            )
        else:
            return func.HttpResponse(
                json.dumps({"error": "Failed to add receipt to the database."}),
                status_code=500,
                headers=headers
            )

    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": "Internal Server Error", "details": str(e)}),
            status_code=500,
            headers=headers
        )
