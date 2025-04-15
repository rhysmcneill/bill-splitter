# billing/helpers/image_utils.py

import os
import tempfile
from PIL import Image
import pillow_heif


def convert_heic_to_jpeg(src_path):

    # Converts a HEIC image to JPEG and returns the new JPEG file path.

    heif_file = pillow_heif.read_heif(src_path)
    image = Image.frombytes(
        heif_file.mode,
        heif_file.size,
        heif_file.data,
        "raw"
    )

    temp_fd, temp_path = tempfile.mkstemp(suffix=".jpg")
    os.close(temp_fd)

    image.save(temp_path, "JPEG")
    return temp_path
