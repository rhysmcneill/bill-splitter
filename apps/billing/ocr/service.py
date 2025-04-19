import os
from decimal import Decimal
from billing.helpers.image_utils import convert_heic_to_jpeg, is_supported_image
from billing.helpers.tabscanner import submit_to_tabscanner, poll_tabscanner_result, is_valid_item


def extract_items_from_receipt(image_path):
    original_ext = os.path.splitext(image_path)[1].lower()

    if not is_supported_image(image_path):
        raise ValueError(f"Unsupported file extension: {original_ext}")

    # Convert HEIC if needed
    temp_jpeg_path = None
    if original_ext in [".heic", ".heif"]:
        print("📸 Converting HEIC image to JPEG...")
        temp_jpeg_path = convert_heic_to_jpeg(image_path)
        image_path = temp_jpeg_path

    token = submit_to_tabscanner(image_path)
    parsed_data = poll_tabscanner_result(token)

    # Clean up temp JPEG file
    if temp_jpeg_path and os.path.exists(temp_jpeg_path):
        os.remove(temp_jpeg_path)

    items = []
    for item in parsed_data.get("lineItems", []):
        desc = item.get("descClean") or item.get("desc", "").strip()
        price = item.get("lineTotal") or item.get("price", 0)
        try:
            if is_valid_item(desc, float(price)):
                items.append({
                    "description": desc,
                    "price": Decimal(str(price)),
                })
        except Exception:
            continue

    # Extract and evaluate OCR confidence
    total_conf = parsed_data.get("totalConfidence", 1)
    sub_conf = parsed_data.get("subTotalConfidence", 1)

    low_confidence = total_conf < 0.80 or sub_conf < 0.80

    return {
        "merchant": parsed_data.get("merchant_name"),
        "date": parsed_data.get("date"),
        "total": parsed_data.get("total"),
        "total_confidence": total_conf,
        "sub_total_confidence": sub_conf,
        "items": items,
        "low_confidence": low_confidence
    }

