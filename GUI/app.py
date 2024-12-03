from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import requests
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
            session['username'] = username
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error="User not found. Please sign up.")
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        result = azure_function_request('AddUser', method='POST', json={'username': username})
        if result and not result.get('error'):
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
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        if result:
            return jsonify({'message': 'Budget set successfully'}), 200
        else:
            return jsonify({'error': 'Failed to set budget'}), 500
    else:
        return redirect(url_for('index'))

@app.route('/view_budgets', methods=['GET'])
def view_budgets():
    if 'username' not in session:
        return jsonify({'error': 'User not logged in'}), 401
    params = {'username': session['username']}
    result = azure_function_request('ViewBudget', method='GET', params=params)
    if result:
        return jsonify({'budgets': result.get('budgets', [])}), 200
    else:
        return jsonify({'error': 'Failed to retrieve budgets'}), 500

@app.route('/update_budget', methods=['POST'])
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
    result = azure_function_request('UpdateBudget', method='PUT', json=data)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        if result:
            return jsonify({'message': 'Budget updated successfully'}), 200
        else:
            return jsonify({'error': 'Failed to update budget'}), 500
    else:
        return redirect(url_for('index'))

@app.route('/delete_budget', methods=['POST'])
def delete_budget():
    if 'username' not in session:
        return jsonify({'error': 'User not logged in'}), 401
    params = {
        'username': session['username'],
        'categoryId': request.form['categoryId']
    }
    result = azure_function_request('DeleteBudget', method='DELETE', params=params)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        if result:
            return jsonify({'message': 'Budget deleted successfully'}), 200
        else:
            return jsonify({'error': 'Failed to delete budget'}), 500
    else:
        return redirect(url_for('index'))

@app.route('/add_expense', methods=['POST'])
def add_expense():
    if 'username' not in session:
        return jsonify({'error': 'User not logged in'}), 401
    data = {
        'username': session['username'],
        'amount': request.form['amount'],
        'date': request.form['date'],
        'description': request.form['description'],
        'categoryId': request.form['categoryId']
    }
    result = azure_function_request('AddExpense', method='POST', json=data)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        if result:
            return jsonify({'message': 'Expense added successfully'}), 200
        else:
            return jsonify({'error': 'Failed to add expense'}), 500
    else:
        return redirect(url_for('index'))
    
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

@app.route('/edit_expense', methods=['POST'])
def edit_expense():
    if 'username' not in session:
        return jsonify({'error': 'User not logged in'}), 401
    data = {
        'username': session['username'],
        'id': request.form['id'],
        'amount': request.form['amount'],
        'date': request.form['date'],
        'description': request.form['description'],
        'categoryId': request.form['categoryId']
    }
    result = azure_function_request('EditExpense', method='POST', json=data)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        if result:
            return jsonify({'message': 'Expense updated successfully'}), 200
        else:
            return jsonify({'error': 'Failed to update expense'}), 500
    else:
        return redirect(url_for('index'))

@app.route('/delete_expense', methods=['POST'])
def delete_expense():
    if 'username' not in session:
        return jsonify({'error': 'User not logged in'}), 401
    params = {
        'username': session['username'],
        'id': request.form['id']
    }
    result = azure_function_request('DeleteExpense', method='DELETE', params=params)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        if result:
            return jsonify({'message': 'Expense deleted successfully'}), 200
        else:
            return jsonify({'error': 'Failed to delete expense'}), 500
    else:
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)