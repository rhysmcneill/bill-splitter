import os
import tempfile
from PIL import Image
import pillow_heif

pillow_heif.register_heif_opener()

SUPPORTED_EXTENSIONS = [".jpg", ".jpeg", ".png", ".heic", ".heif"]


def convert_heic_to_jpeg(src_path):

    # Converts a HEIC/HEIF image to JPEG and returns the new temp file path.

    heif_file = pillow_heif.read_heif(src_path)
    image = Image.frombytes(heif_file.mode, heif_file.size, heif_file.data, "raw")

    temp_fd, temp_path = tempfile.mkstemp(suffix=".jpg")
    os.close(temp_fd)

    image.save(temp_path, "JPEG")
    return temp_path


def is_supported_image(path):

    # Checks if the file extension is supported for upload.

    ext = os.path.splitext(path)[1].lower()
    return ext in SUPPORTED_EXTENSIONS
