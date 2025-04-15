import os
from decimal import Decimal
from billing.helpers.image_utils import convert_heic_to_jpeg
from billing.helpers.tabscanner import submit_to_tabscanner, poll_tabscanner_result


def extract_items_from_receipt(image_path):
    """
    Submit image to Tabscanner, wait for result, return structured line items.
    """
    original_ext = os.path.splitext(image_path)[1].lower()

    if original_ext == ".heic":
        print("📸 Converting HEIC image to JPEG...")
        image_path = convert_heic_to_jpeg(image_path)

    token = submit_to_tabscanner(image_path)
    parsed_data = poll_tabscanner_result(token)

    # Optionally remove temp file if it was HEIC → JPEG
    if original_ext == ".heic" and os.path.exists(image_path):
        os.remove(image_path)

    items = []
    for item in parsed_data.get("items", []):
        if item.get("description") and item.get("amount"):
            try:
                items.append({
                    "description": item["description"].strip(),
                    "price": Decimal(item["amount"]),
                    "quantity": int(item.get("quantity") or 1),
                })
            except Exception:
                continue

    return {
        "merchant": parsed_data.get("merchant_name"),
        "date": parsed_data.get("date"),
        "total": parsed_data.get("total"),
        "items": items
    }
