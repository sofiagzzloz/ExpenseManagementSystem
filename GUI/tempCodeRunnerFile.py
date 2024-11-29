from flask import Flask, render_template, request, flash
import os, socket, requests

app = Flask(__name__)

app.secret_key = os.environ.get("APP_SECRET_KEY", "my_default_secret_key")

add_expense_url = "https://expensefuncapp.azurewebsites.net/api/AddExpense?code=2_Ugg1lTFT3PYiPuWBxPAH-9xlf9wJTiBQOWIW3zC0f-AzFu3p-5Kw%3D%3D"
add_expense_key = "2_Ugg1lTFT3PYiPuWBxPAH-9xlf9wJTiBQOWIW3zC0f-AzFu3p-5Kw=="  

hostname = socket.gethostname()

# Homepage route to render the form
@app.route('/')
def index():
    return render_template('index.html', expenses=None)  # By default, no expenses are passed

# Add expense form submission route
@app.route('/add-expense', methods=['POST'])
def add_expense():
    try:
        # Collect form data
        expense_data = {
            "userId": request.form.get("userId"),
            "amount": request.form.get("amount"),
            "date": request.form.get("date"),
            "description": request.form.get("description"),
            "categoryId": request.form.get("categoryId"),
        }

        # Send POST request to Azure Function
        response = requests.post(
            add_expense_url,  # URL already includes the code parameter
            json=expense_data,  # The data to send
            headers={"Content-Type": "application/json"},  # Ensure correct headers
        )
        response.raise_for_status()

        flash("Expense added successfully!", "success")
    except requests.exceptions.RequestException as e:
        flash(f"An error occurred while sending the request: {e}", "error")
    except Exception as e:
        flash(f"An unexpected error occurred: {e}", "error")

    return render_template('index.html')
if __name__ == '__main__':
    app.run(debug = True)