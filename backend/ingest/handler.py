"""
Ingest Lambda — triggered by EventBridge on a schedule.
Fetches conditions from Open-Meteo and OnTheSnow, writes to DynamoDB.
"""

import json
import os
from decimal import Decimal
import boto3
from shared.resorts import RESORTS
from open_meteo import fetch_resort_forecast, extract_windows
from onthesnow import fetch_all_snapshots

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["CONDITIONS_TABLE"])


def lambda_handler(event, context):
    print("Ingest started")

    # 1. Fetch live lift/base data for all resorts
    snapshots = fetch_all_snapshots()

    # 2. Fetch and process weather forecast for each resort
    for resort_key, resort in RESORTS.items():
        forecast_raw = fetch_resort_forecast(
            lat=resort["lat"],
            lon=resort["lon"],
            elevation_high=resort["elevation_high"],
            elevation_mid=resort["elevation_mid"],
        )
        windows = extract_windows(forecast_raw["hourly"])
        snapshot = snapshots[resort_key]

        # 3. Write to DynamoDB — floats must be Decimal for boto3
        item = {
            "resort": resort_key,
            "forecast_windows": windows,
            "lifts_open": snapshot["lifts_open"],
            "lifts_total": snapshot["lifts_total"],
            "base_depth_cm": snapshot["base_depth_cm"],
        }
        item = json.loads(json.dumps(item), parse_float=Decimal)
        table.put_item(Item=item)
        print(f"Written {resort_key}")

    return {"statusCode": 200, "body": "Ingest complete"}
