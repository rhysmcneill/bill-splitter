import requests
import json
import time
from django.conf import settings
from decimal import Decimal

TABSCANNER_API_KEY = settings.TABSCANNER_API_KEY
TABSCANNER_PROCESS_ENDPOINT = "https://api.tabscanner.com/api/2/process"
TABSCANNER_RESULT_ENDPOINT = "https://api.tabscanner.com/api/result/{}"


def submit_to_tabscanner(image_path):
    headers = {"apikey": TABSCANNER_API_KEY}
    data = {"documentType": "receipt"}

    with open(image_path, "rb") as f:
        files = {"file": f}
        response = requests.post(TABSCANNER_PROCESS_ENDPOINT, data=data, files=files, headers=headers)
        result = response.json()

    if not result.get("success") or "token" not in result:
        raise ValueError("Tabscanner process failed: " + str(result))

    return result["token"]


def poll_tabscanner_result(token, max_retries=20, delay=2):
    url = TABSCANNER_RESULT_ENDPOINT.format(token)
    headers = {"apikey": TABSCANNER_API_KEY}

    for attempt in range(max_retries):
        response = requests.get(url, headers=headers)
        data = response.json()
        print(f"[Tabscanner] Poll attempt {attempt + 1} response:", data)

        if not data.get("success"):
            raise ValueError("Tabscanner result failed: " + str(data))

        status = data.get("status")
        if status == "done":
            return data["result"]

        time.sleep(delay)

    raise TimeoutError("Tabscanner processing timed out.")


def is_valid_item(desc: str, price: float) -> bool:
    if not desc or not isinstance(price, (int, float, Decimal)) or price <= 0:
        return False

    desc_lower = desc.strip().lower()

    # More precise keyword matching (whole terms or very specific)
    junk_keywords = [
        'subtotal', 'total', 'grand total', 'tax', 'tip', 'change',
        'service charge', 'table', 'thank you', 'cash', 'card', 'vat', 'rounding'
    ]

    return not any(kw in desc_lower for kw in junk_keywords)
