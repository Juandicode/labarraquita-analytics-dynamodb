import json
import os
import boto3
from datetime import datetime, timezone
from decimal import Decimal

dynamodb = boto3.resource("dynamodb")
TABLE_NAME = os.environ.get("TABLE_NAME", "analytics-eventos")
table = dynamodb.Table(TABLE_NAME)

# Headers CORS — necesarios porque el request va a venir desde el navegador
# del visitante (otro origen), no desde un backend.
CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
}


def lambda_handler(event, context):
    # API Gateway manda un preflight OPTIONS antes del POST real cuando hay CORS.
    # Hay que responder OK sin hacer nada más.
    if event.get("requestContext", {}).get("http", {}).get("method") == "OPTIONS":
        return {"statusCode": 200, "headers": CORS_HEADERS, "body": ""}

    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return _response(400, {"error": "Body inválido"})

    sitio_id = body.get("sitio_id")
    evento = body.get("evento")

    # Validación mínima: sin estos dos campos, el evento no sirve para nada.
    if not sitio_id or not evento:
        return _response(400, {"error": "Faltan campos: sitio_id y evento son obligatorios"})

    item = {
        "sitio_id": sitio_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "evento": evento,
        "referrer": body.get("referrer", ""),
        "producto": body.get("producto", ""),
        "user_agent": event.get("headers", {}).get("user-agent", ""),
    }

    table.put_item(Item=item)

    return _response(200, {"ok": True})


def _response(status_code, body_dict):
    return {
        "statusCode": status_code,
        "headers": {**CORS_HEADERS, "Content-Type": "application/json"},
        "body": json.dumps(body_dict),
    }