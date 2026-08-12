"""
API Lambda — handles GET /conditions and POST /recommend.
Triggered by API Gateway (HTTP API, payload format 2.0).
"""

import json
import os
from decimal import Decimal

import boto3

from scorer import rank
from overview import format_overview
from explain import generate_why

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["CONDITIONS_TABLE"])


def lambda_handler(event, context):
    http = event["requestContext"]["http"]
    method = http["method"]
    path = http["path"]

    if method == "GET" and path == "/conditions":
        conditions = _load_conditions()
        if not conditions:
            return _err(503, "Conditions not available yet — ingest has not run.")
        return _ok(format_overview(conditions))

    if method == "POST" and path == "/recommend":
        try:
            preferences = json.loads(event.get("body") or "{}")
        except json.JSONDecodeError:
            return _err(400, "Invalid JSON body.")
        if not preferences.get("selected_dates"):
            return _err(400, "selected_dates is required.")
        conditions = _load_conditions()
        if not conditions:
            return _err(503, "Conditions not available yet — ingest has not run.")
        return _ok(generate_why(rank(conditions, preferences), preferences))

    return _err(404, f"No route for {method} {path}.")


def _load_conditions() -> dict:
    """
    Read all resort items from DynamoDB.
    Returns { resort_key: item_dict } with Decimals converted to float.
    Returns an empty dict if the table has no items yet (ingest hasn't run).
    """
    response = table.scan()
    return {
        item["resort"]: _to_python({k: v for k, v in item.items() if k != "resort"})
        for item in response.get("Items", [])
    }


def _to_python(obj):
    """Recursively convert DynamoDB Decimals to float."""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, dict):
        return {k: _to_python(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_python(v) for v in obj]
    return obj


def _ok(data) -> dict:
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(data),
    }


def _err(status: int, message: str) -> dict:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"error": message}),
    }
