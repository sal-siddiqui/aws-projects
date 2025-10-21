# ruff: noqa
# lambda_function.py
# AWS Lambda function for employee management API.
# Handles CRUD operations for employee records stored in DynamoDB.

import json
import logging
import uuid
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError

# Initialize AWS resources and logging
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("employees")

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class DecimalEncoder(json.JSONEncoder):
    """JSON encoder that handles Decimal types from DynamoDB."""

    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super().default(obj)


class EmployeeNotFoundError(Exception):
    """Custom exception for when an employee record is not found."""

    pass


def lambda_handler(event, context):
    """Main Lambda handler that routes HTTP requests to appropriate functions."""
    logger.info("Received event: %s", event)

    # Extract HTTP method and path from event
    method = event["requestContext"]["http"]["method"]
    path = event["requestContext"]["http"]["path"]
    logger.debug("Method: %s | Path: %s", method, path)

    # Parse request parameters and body
    params = event.get("queryStringParameters", {})
    body = json.loads(event.get("body", "{}"))
    logger.debug("Query Params: %s | Body: %s", params, body)

    # Route requests to appropriate handlers
    if "info" in path.split("/"):
        logger.info("Info endpoint requested.")
        return make_response(event)

    # GET endpoints
    if method == "GET":
        if path == "/employees":
            return get_employees()
        if path.startswith("/employees/"):
            employee_id = path.split("/")[-1]
            return get_employee(employee_id)

    # POST endpoints
    if method == "POST" and path == "/employees":
        return create_employee(body)

    # PATCH endpoints
    if method == "PATCH" and path.startswith("/employees/"):
        employee_id = path.split("/")[-1]
        return update_employee(employee_id, body)

    # DELETE endpoints
    if method == "DELETE" and path.startswith("/employees/"):
        employee_id = path.split("/")[-1]
        return delete_employee(employee_id)

    logger.warning("Unhandled method or path: %s %s", method, path)
    return make_response({"error": "Method Not Implemented"}, 501)


def get_employee(employee_id):
    """Retrieve a single employee by ID."""
    try:
        logger.info("Fetching employee with ID: '%s'", employee_id)
        employee = get_or_throw(employee_id)
        logger.debug("Employee fetched: '%s'", employee)
        return make_response(employee)
    except EmployeeNotFoundError as e:
        logger.warning(str(e))
        return make_response({"error": str(e)}, 404)
    except ClientError as e:
        logger.exception("AWS client error while fetching employee")
        error_message = e.response.get("Error", {}).get("Message", str(e))
        return make_response({"error": error_message}, 500)


def get_employees():
    """Retrieve all employees from the database."""
    logger.info("Scanning all employees")
    try:
        employees = []
        response = table.scan()
        employees.extend(response.get("Items", []))
        logger.debug("Fetched %d employees", len(employees))

        # Handle pagination for large datasets
        while "LastEvaluatedKey" in response:
            response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
            employees.extend(response.get("Items", []))
            logger.debug("Continuing scan, total so far: %d", len(employees))

        return make_response(employees)
    except ClientError as e:
        logger.exception("AWS client error while scanning employees")
        error_message = e.response.get("Error", {}).get("Message", str(e))
        return make_response({"error": error_message}, 500)


def create_employee(employee_data):
    """Create a new employee record."""
    employee_id = str(uuid.uuid4())
    logger.info("Creating new employee: %s", employee_id)

    try:
        table.put_item(Item={"id": employee_id, **employee_data})
        logger.debug("Employee created successfully: %s", employee_id)
        return make_response({"id": employee_id}, 201)
    except ClientError as e:
        logger.exception("AWS client error while creating employee")
        error_message = e.response.get("Error", {}).get("Message", str(e))
        return make_response({"error": error_message}, 500)


def update_employee(employee_id, update_data):
    """Update specific attributes of an employee record."""
    logger.info("Updating employee: %s | Data: %s", employee_id, update_data)

    try:
        get_or_throw(employee_id)  # Verify employee exists

        response = table.update_item(
            Key={"id": employee_id},
            ExpressionAttributeNames={"#attr": update_data["attribute"]},
            ExpressionAttributeValues={":value": update_data["value"]},
            UpdateExpression="SET #attr = :value",
            ReturnValues="UPDATED_NEW",
        )
        logger.debug("Employee updated: %s", response["Attributes"])
        return make_response(response["Attributes"])
    except EmployeeNotFoundError as e:
        logger.warning(str(e))
        return make_response({"error": str(e)}, 404)
    except ClientError as e:
        logger.exception("AWS client error while updating employee")
        error_message = e.response.get("Error", {}).get("Message", str(e))
        return make_response({"error": error_message}, 500)


def delete_employee(employee_id):
    """Delete an employee record."""
    try:
        get_or_throw(employee_id)  # Verify employee exists
        logger.info("Deleting employee: %s", employee_id)

        table.delete_item(Key={"id": employee_id})
        logger.debug("Employee deleted: %s", employee_id)
        return make_response(None, 204)
    except EmployeeNotFoundError as e:
        logger.warning(str(e))
        return make_response({"error": str(e)}, 404)
    except ClientError as e:
        logger.exception("AWS client error while deleting employee")
        error_message = e.response.get("Error", {}).get("Message", str(e))
        return make_response({"error": error_message}, 500)


def get_or_throw(employee_id):
    """Internal helper to get employee or raise EmployeeNotFound exception."""
    result = table.get_item(Key={"id": employee_id})
    employee = result.get("Item")

    if not employee:
        logger.warning("Employee %s not found", employee_id)
        message = f"Employee {employee_id!r} not found"
        raise EmployeeNotFoundError(message)

    return employee


def make_response(body, status_code=200):
    """Create a standardized HTTP response."""
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, cls=DecimalEncoder),
    }
