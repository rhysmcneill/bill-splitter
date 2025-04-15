import requests
import json
import time
from django.conf import settings

TABSCANNER_API_KEY = settings.TABSCANNER_API_KEY
TABSCANNER_PROCESS_ENDPOINT = "https://api.tabscanner.com/api/2/process"
TABSCANNER_RESULT_ENDPOINT = "https://api.tabscanner.com/api/result/{}"


def submit_to_tabscanner(image_path):

    # Send image to Tabscanner and get a processing token.

    headers = {
        "apikey": TABSCANNER_API_KEY
    }
    data = {
        "documentType": "receipt"
    }

    with open(image_path, "rb") as f:
        files = {"file": f}
        response = requests.post(TABSCANNER_PROCESS_ENDPOINT, data=data, files=files, headers=headers)
        result = response.json()

    if not result.get("success") or "token" not in result:
        raise ValueError("Tabscanner process failed: " + str(result))

    return result["token"]


def poll_tabscanner_result(token, max_retries=10, delay=2):

    # Poll Tabscanner for structured result.

    url = TABSCANNER_RESULT_ENDPOINT.format(token)
    headers = {
        "apikey": TABSCANNER_API_KEY
    }

    for attempt in range(max_retries):
        response = requests.get(url, headers=headers)
        data = response.json()

        if not data.get("success"):
            raise ValueError("Tabscanner result failed: " + str(data))

        status = data["data"]["status"]

        if status == "completed":
            return data["data"]["results"]

        print(f"[Tabscanner] Waiting for result... attempt {attempt + 1}")
        time.sleep(delay)

    raise TimeoutError("Tabscanner processing timed out.")
