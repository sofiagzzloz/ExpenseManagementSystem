from flask import Flask, render_template, request, jsonify
import requests
from dotenv import load_dotenv
import os
import logging 

load_dotenv()  # Load environment variables from .env file

app = Flask(__name__)

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
    'DeleteExpense': os.getenv('DELETE_EXPENSE_KEY')
}

def azure_function_request(function_name, method='GET', params=None, json=None):
    url = f"{AZURE_FUNCTIONS_BASE_URL}/{function_name}"
    headers = {'x-functions-key': FUNCTION_KEYS[function_name]}
    
    try:
        if method == 'GET':
            response = requests.get(url, headers=headers, params=params)
        elif method == 'POST':
            response = requests.post(url, headers=headers, json=json)
        elif method == 'DELETE':
            response = requests.delete(url, headers=headers, params=params)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        logging.error(f"Error calling Azure function {function_name}: {str(e)}")
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/set_budget', methods=['POST'])
def set_budget():
    data = {
        'userId': request.form['userId'],
        'categoryId': request.form['categoryId'],
        'budgetLimit': request.form['budgetLimit'],
        'startDate': request.form['startDate'],
        'endDate': request.form['endDate']
    }
    response = azure_function_request('SetBudget', method='POST', json=data)
    if response.status_code == 200:
        return jsonify({'message': 'Budget set successfully'}), 200
    else:
        return jsonify({'error': 'Failed to set budget'}), 500

@app.route('/view_budget', methods=['GET'])
def view_budget():
    params = {
        'userId': request.args.get('userId'),
        'categoryId': request.args.get('categoryId')
    }
    response = azure_function_request('ViewBudget', method='GET', params=params)
    if response.status_code == 200:
        budget = response.json()['budget']
        return jsonify({'budget': budget}), 200
    else:
        return jsonify({'error': 'Failed to retrieve budget'}), 500

@app.route('/update_budget', methods=['POST'])
def update_budget():
    data = {
        'userId': request.form['userId'],
        'categoryId': request.form['categoryId'],
        'budgetLimit': request.form['budgetLimit'],
        'startDate': request.form['startDate'],
        'endDate': request.form['endDate']
    }
    response = azure_function_request('UpdateBudget', method='POST', json=data)
    if response.status_code == 200:
        return jsonify({'message': 'Budget updated successfully'}), 200
    else:
        return jsonify({'error': 'Failed to update budget'}), 500

@app.route('/delete_budget', methods=['POST'])
def delete_budget():
    params = {
        'userId': request.form['userId'],
        'categoryId': request.form['categoryId']
    }
    response = azure_function_request('DeleteBudget', method='DELETE', params=params)
    if response.status_code == 200:
        return jsonify({'message': 'Budget deleted successfully'}), 200
    else:
        return jsonify({'error': 'Failed to delete budget'}), 500

@app.route('/add_expense', methods=['POST'])
def add_expense():
    data = {
        'userId': request.form['userId'],
        'amount': request.form['amount'],
        'date': request.form['date'],
        'description': request.form['description'],
        'categoryId': request.form['categoryId']
    }
    response = azure_function_request('AddExpense', method='POST', json=data)
    if response.status_code == 200:
        return jsonify({'message': 'Expense added successfully'}), 200
    else:
        return jsonify({'error': 'Failed to add expense'}), 500

@app.route('/view_expense', methods=['GET'])
def view_expense():
    params = {
        'userId': request.args.get('userId'),
        'categoryId': request.args.get('categoryId'),
        'startDate': request.args.get('startDate'),
        'endDate': request.args.get('endDate')
    }
    response = azure_function_request('ViewExpense', method='GET', params=params)
    if response.status_code == 200:
        expenses = response.json()['expenses']
        return jsonify({'expenses': expenses}), 200
    else:
        return jsonify({'error': 'Failed to retrieve expenses'}), 500

@app.route('/edit_expense', methods=['POST'])
def edit_expense():
    data = {
        'id': request.form['id'],
        'amount': request.form['amount'],
        'date': request.form['date'],
        'description': request.form['description'],
        'categoryId': request.form['categoryId']
    }
    response = azure_function_request('EditExpense', method='POST', json=data)
    if response.status_code == 200:
        return jsonify({'message': 'Expense updated successfully'}), 200
    else:
        return jsonify({'error': 'Failed to update expense'}), 500

@app.route('/delete_expense', methods=['POST'])
def delete_expense():
    params = {'id': request.form['id']}
    response = azure_function_request('DeleteExpense', method='DELETE', params=params)
    if response.status_code == 200:
        return jsonify({'message': 'Expense deleted successfully'}), 200
    else:
        return jsonify({'error': 'Failed to delete expense'}), 500

if __name__ == '__main__':
    app.run(debug=True)