import logging
import azure.functions as func
import json
from azure.storage.queue import QueueClient
import datetime

# Azure Storage Queue Configuration
queue_connection_string = "DefaultEndpointsProtocol=https;AccountName=expensemanagement777;AccountKey=20vipKb66lGG3vXuFZCRiBIhpHW+kL7NYXoPiAPobWNDmsm0S+sjQ8AI4L6atUimKH8mS5tNOCMn+AStPzGfEQ==;EndpointSuffix=core.windows.net"
queue_name = "deadletterqueue"

def send_to_dead_letter_queue(message):
    """
    Send a message to the Dead Letter Queue.
    """
    try:
        # Initialize the queue client
        queue_client = QueueClient.from_connection_string(queue_connection_string, queue_name)

        # Ensure message is JSON-encoded
        queue_client.send_message(json.dumps(message))
        logging.info(f"Message successfully sent to Dead Letter Queue: {message}")

    except Exception as e:
        logging.error(f"Failed to send message to Dead Letter Queue: {str(e)}")
        raise e

def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Processes incoming HTTP requests and logs invalid requests to the Dead Letter Queue.
    """
    logging.info('Processing HTTP request for Dead Letter Queue example.')

    try:
        # Parse the request body
        req_body = req.get_json()

        # Validation logic (customize based on your requirements)
        required_fields = ['userId', 'amount', 'date', 'description', 'categoryId']
        missing_fields = [field for field in required_fields if not req_body.get(field)]

        if missing_fields:
            # Log invalid request to Dead Letter Queue
            invalid_request = {
                "requestBody": req_body,
                "error": f"Missing required fields: {', '.join(missing_fields)}",
                "timestamp": datetime.datetime.utcnow().isoformat()
            }
            send_to_dead_letter_queue(invalid_request)

            return func.HttpResponse(
                json.dumps({"message": "Invalid request logged to Dead Letter Queue"}),
                status_code=400,
                headers={"Content-Type": "application/json"}
            )

        # Handle valid requests (e.g., business logic here)
        return func.HttpResponse(
            json.dumps({"message": "Request is valid"}),
            status_code=200,
            headers={"Content-Type": "application/json"}
        )

    except ValueError:
        # Handle JSON parsing errors
        invalid_request = {
            "requestBody": None,
            "error": "Invalid JSON format",
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
        send_to_dead_letter_queue(invalid_request)

        return func.HttpResponse(
            json.dumps({"message": "Invalid JSON format, logged to Dead Letter Queue"}),
            status_code=400,
            headers={"Content-Type": "application/json"}
        )

    except Exception as e:
        # Handle unexpected errors
        invalid_request = {
            "requestBody": None,
            "error": str(e),
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
        send_to_dead_letter_queue(invalid_request)

        return func.HttpResponse(
            json.dumps({"message": "An error occurred, logged to Dead Letter Queue"}),
            status_code=500,
            headers={"Content-Type": "application/json"}
        )