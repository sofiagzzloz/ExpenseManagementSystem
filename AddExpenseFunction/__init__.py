import logging
import os
import json
import azure.functions as func
from azure.core.exceptions import HttpResponseError
from azure.storage.blob import BlobServiceClient
from models import db, Expense, Category  # Ensure Expense model is correctly defined
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Fetch the environment variables for Azure Storage and MySQL
AZURE_STORAGE_CONNECTION_STRING = os.getenv('AzureWebJobsStorage')
DATABASE_URI = (
    f"mysql+mysqlconnector://{os.getenv('db_username')}:{os.getenv('db_password')}"
    f"@{os.getenv('db_host')}/{os.getenv('db_name')}"
)

# Create SQLAlchemy engine and session for MySQL database
engine = create_engine(DATABASE_URI)
Session = sessionmaker(bind=engine)
db_session = Session()

# Azure Blob Storage Configuration
CONTAINER_NAME = "receipts"  # The name of your container where receipts will be stored
blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
container_client = blob_service_client.get_container_client(CONTAINER_NAME)

# Function to handle POST request for adding an expense
def add_expense(req: func.HttpRequest) -> func.HttpResponse:
    try:
        # Parse incoming JSON data
        req_body = req.get_json()
        
        # Extract data from the request
        amount = req_body.get('amount')
        category = req_body.get('category')
        date = req_body.get('date')
        description = req_body.get('description')
        receipt = req_body.get('receipt')  # Assume receipt is base64 or a URL (if file)

        # Validate inputs
        if not all([amount, category, date]):
            return func.HttpResponse(
                json.dumps({"message": "Missing required fields: 'amount', 'category', or 'date'.", "status": "error"}),
                status_code=400,
                mimetype="application/json"
            )

        # Handle receipt upload to Azure Blob Storage
        receipt_path = None
        if receipt:
            file_name = f"{category}_{date}_{amount}.jpg"  # Example naming scheme
            blob_client = container_client.get_blob_client(file_name)
            receipt_data = receipt.encode("utf-8")  # If it's base64 data, decode it accordingly
            blob_client.upload_blob(receipt_data, overwrite=True)  # Overwrite if exists
            receipt_path = blob_client.url  # The URL to the blob in Azure Storage

        # Create new expense record in the database
        new_expense = Expense(
            amount=amount,
            category=category,
            date=date,
            description=description,
            receipt_path=receipt_path
        )

        # Add expense to database using the session
        db_session.add(new_expense)
        db_session.commit()

        # Return success response
        return func.HttpResponse(
            json.dumps({"message": "Expense added successfully", "status": "success"}),
            status_code=200,
            mimetype="application/json"
        )

    except HttpResponseError as e:
        logging.error(f"Error while adding expense: {str(e)}")
        return func.HttpResponse(
            json.dumps({"message": str(e), "status": "error"}),
            status_code=500,
            mimetype="application/json"
        )