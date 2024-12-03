from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import requests
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv
import os
import logging

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY')  # Make sure to set this in your .env file
logging.basicConfig(level=logging.INFO)

AZURE_FUNCTIONS_BASE_URL = os.getenv('AZURE_FUNCTIONS_BASE_URL')

# Load function keys from environment variables
FUNCTION_KEYS = {
    'SetBudget': os.getenv('SET_BUDGET_KEY'),
    'ViewBudget': os.getenv('VIEW_BUDGET_KEY'),
    'UpdateBudget': os.getenv('UPDATE_BUDGET_KEY'),
    'DeleteBudget': os.getenv('DELETE_BUDGET_KEY'),
    'AddExpense': os.getenv('ADD_EXPENSE_KEY'),
    'ViewExpense': os.getenv('VIEW_EXPENSE_KEY'),
    'EditExpense': os.getenv('EDIT_EXPENSE_KEY'),
    'DeleteExpense': os.getenv('DELETE_EXPENSE_KEY'),
    'AddUser': os.getenv('ADD_USER_KEY'),
    'GetUser': os.getenv('GET_USER_KEY')
}

def azure_function_request(function_name, method='GET', params=None, json=None):
    url = f"{AZURE_FUNCTIONS_BASE_URL}/{function_name}"
    headers = {'x-functions-key': FUNCTION_KEYS[function_name]}
    
    try:
        if method == 'GET':
            response = requests.get(url, headers=headers, params=params)
        elif method == 'POST':
            response = requests.post(url, headers=headers, json=json)
        elif method == 'PUT':  # Add support for PUT requests
            response = requests.put(url, headers=headers, json=json)
        elif method == 'DELETE':
            response = requests.delete(url, headers=headers, params=params)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error calling Azure function {function_name}: {str(e)}")
        return None

@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        result = azure_function_request('GetUser', method='GET', params={'username': username})
        
        if result and result.get('exists'):
            # If the user exists, log them in and set the session
            session['username'] = username
            # Optionally, you can pass a success message here
            return redirect(url_for('index'))  # Redirecting to the index page
        else:
            # If the user doesn't exist, show an error message
            return render_template('login.html', error="User not found. Please sign up.")
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        result = azure_function_request('AddUser', method='POST', json={'username': username})
        if result:
            if result.get('error'):
                return render_template('signup.html', error="Username already exists.")
            session['username'] = username
            return redirect(url_for('index'))
        else:
            return render_template('signup.html', error="Error occurred while signing up.")
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/set_budget', methods=['POST'])
def set_budget():
    if 'username' not in session:
        return jsonify({'error': 'User not logged in'}), 401
    data = {
        'username': session['username'],
        'categoryId': request.form['categoryId'],
        'budgetLimit': request.form['budgetLimit'],
        'startDate': request.form['startDate'],
        'endDate': request.form['endDate']
    }
    result = azure_function_request('SetBudget', method='POST', json=data)
    if result:
        return jsonify({'message': 'Budget set successfully'}), 200
    else:
        return jsonify({'error': 'Failed to set budget'}), 500
    
    return render_template('index.html')

@app.route('/view_budgets', methods=['GET'])
def view_budgets():
    if 'username' not in session:
        return jsonify({'error': 'User not logged in'}), 401

    params = {
        'username': session['username']
    }
    result = azure_function_request('ViewBudget', method='GET', params=params)

    if result:
        # Log the response to verify the data structure
        logging.info(f"ViewBudget response: {result}")

        # Ensure the frontend gets a proper JSON response
        return jsonify({'budgets': result.get('budgets', [])}), 200
    else:
        logging.error("Failed to retrieve budgets.")
        return jsonify({'error': 'Failed to retrieve budgets', 'budgets': []}), 500
    
    return render_template('index.html')

@app.route('/update_budget', methods=['PUT'])
def update_budget():
    if 'username' not in session:
        return jsonify({'error': 'User not logged in'}), 401

    data = {
        'username': session['username'],
        'categoryId': request.form['categoryId'],
        'budgetLimit': request.form['budgetLimit'],
        'startDate': request.form['startDate'],
        'endDate': request.form['endDate']
    }
    logging.info(f"Updating budget with data: {data}")

    try:
        result = azure_function_request('UpdateBudget', method='PUT', json=data)
        logging.info(f"UpdateBudget response: {result}")

        if result:
            return jsonify({'message': 'Budget updated successfully'}), 200
        else:
            logging.error('Failed to update budget.')
            return jsonify({'error': 'Failed to update budget'}), 500
    except Exception as e:
        logging.error(f"Error in /update_budget: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500
    
    return render_template('index.html')

@app.route('/delete_budget', methods=['POST'])
def delete_budget():
    if 'username' not in session:
        return jsonify({'error': 'User not logged in'}), 401
    params = {
        'username': session['username'],
        'categoryId': request.form['categoryId']
    }
    result = azure_function_request('DeleteBudget', method='DELETE', params=params)
    if result:
        return jsonify({'message': 'Budget deleted successfully'}), 200
    else:
        return jsonify({'error': 'Failed to delete budget'}), 500
    
    return render_template('index.html')

@app.route('/add_expense', methods=['POST'])
def add_expense():
    # Retrieve form data
    amount = request.form.get('amount')
    date = request.form.get('date')
    description = request.form.get('description')
    category_id = request.form.get('categoryId')
    receipt_file = request.files.get('file')  # Optional file input

    # Prepare the data for the AddExpense function
    data = {
        'amount': amount,
        'date': date,
        'description': description,
        'categoryId': category_id,
        'username': session['username']  # Assume `username` is stored in session
    }

    # Call the AddExpense Azure Function
    expense_result = azure_function_request('AddExpense', method='POST', json=data)

    if not expense_result or 'id' not in expense_result:
        logging.error('Failed to add expense.')
        return jsonify({'error': 'Failed to add expense'}), 500

    expense_id = expense_result['id']  # Get the generated expense ID from the response

    # Handle receipt upload if a file was provided
    if receipt_file:
        receipt_response = requests.post(
            f"{AZURE_FUNCTIONS_BASE_URL}/AddReceipt",
            headers={'x-functions-key': FUNCTION_KEYS['AddReceipt']},
            files={'file': (receipt_file.filename, receipt_file.stream, receipt_file.mimetype)},
            data={'expenseId': expense_id}
        )
        if receipt_response.status_code != 200:
            logging.error('Receipt upload failed.')
            return jsonify({'error': 'Expense added, but receipt upload failed.'}), 500

    return jsonify({'message': 'Expense added successfully!'}), 200

@app.route('/view_expenses', methods=['GET'])
def view_expenses():
    if 'username' not in session:
        return jsonify({'error': 'User not logged in'}), 401

    params = {
        'username': session['username'],
        'categoryId': request.args.get('categoryId'),
        'startDate': request.args.get('startDate'),
        'endDate': request.args.get('endDate')
    }
    logging.info(f"Fetching expenses with params: {params}")

    try:
        result = azure_function_request('ViewExpense', method='GET', params=params)
        logging.info(f"ViewExpenses response: {result}")

        if result and 'data' in result:
            # Map the 'data' key to 'expenses' for frontend compatibility
            return jsonify({'expenses': result['data']}), 200
        else:
            logging.error('No data returned by Azure function or incorrect format.')
            return jsonify({'error': 'Failed to retrieve expenses'}), 500
    except Exception as e:
        logging.error(f"Error in /view_expenses: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500
    
    return render_template('index.html')

@app.route('/edit_expense', methods=['POST'])
def edit_expense():
    if 'username' not in session:
        return jsonify({'error': 'User not logged in'}), 401

    try:
        data = {
            'id': int(request.form['id']),  # Expense ID
            'userId': None,  # Optional
            'amount': float(request.form['amount']) if 'amount' in request.form else None,
            'date': request.form['date'] if 'date' in request.form else None,
            'description': request.form['description'] if 'description' in request.form else None,
            'categoryId': int(request.form['categoryId']) if 'categoryId' in request.form else None,
            'status': request.form['status'] if 'status' in request.form else None
        }

        logging.info(f"Sending data to EditExpense: {data}")
        result = azure_function_request('EditExpense', method='PUT', json=data)

        if result:
            logging.info(f"EditExpense response: {result}")
            return jsonify({'message': 'Expense updated successfully'}), 200
        else:
            logging.error('Failed to update expense: Azure function returned no result.')
            return jsonify({'error': 'Failed to update expense'}), 500
    except ValueError as ve:
        logging.error(f"Input validation error: {str(ve)}")
        return jsonify({'error': 'Invalid input provided'}), 400
    except Exception as e:
        logging.error(f"Unexpected error in /edit_expense: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/delete_expense', methods=['POST'])
def delete_expense():
    if 'username' not in session:
        return jsonify({'error': 'User not logged in'}), 401
    params = {
        'username': session['username'],
        'id': request.form['id']
    }
    result = azure_function_request('DeleteExpense', method='DELETE', params=params)
    if result:
        return jsonify({'message': 'Expense deleted successfully'}), 200
    else:
        return jsonify({'error': 'Failed to delete expense'}), 500
    
    return render_template('index.html')

@app.route('/add_receipt', methods=['POST'])
def add_receipt():
    try:
        expense_id = request.form['expenseId']
        file = request.files['file']

        if not expense_id or not file:
            return jsonify({"error": "Expense ID and file are required."}), 400

        # Call Azure Function to handle receipt upload
        files = {'file': (file.filename, file.stream, file.content_type)}
        data = {'expenseId': expense_id}

        response = azure_function_request('AddReceipt', method='POST', files=files, data=data)

        if 'error' in response:
            return jsonify({"error": response['error']}), 500

        return jsonify({"message": "Receipt uploaded successfully!"})
    except Exception as e:
        logging.error(f"Error adding receipt: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(debug=True)