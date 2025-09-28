import os
import random
import re
import string
from pathlib import Path
from typing import Pattern


def generate_uuid() -> str:
    # Combine uppercase letters, lowercase letters, and digits
    characters: str = string.ascii_letters + string.digits

    # Generate a random 4-character code
    random_code: str = "".join(random.choice(characters) for _ in range(4))

    return random_code


def extract_extension(file_name: Path) -> str:
    _, extension = os.path.splitext(file_name)
    return extension


def extract_uuid(uuid_string):
    # Check if the string ends with .txt or any extension
    if "." in uuid_string:
        # Split at the last occurrence of '.' and return the first part
        return uuid_string.rsplit(".", 1)[0]
    # If no extension, return the original string
    return uuid_string


def _find_without_extension(file_name: str) -> str:
    file_list: list = os.listdir("data")
    pattern_with_dot: Pattern[str] = re.compile(r"^(" + re.escape(file_name) + r")\.")
    pattern_without_dot: Pattern[str] = re.compile(r"^" + file_name + "$")
    math_pattern: list = [x for x in file_list if pattern_with_dot.match(x) or pattern_without_dot.match(x)]
    if len(math_pattern) == 0:
        return str()
    else:
        return math_pattern[0]


def _filter_object_name_from_link(link: str) -> str:
    """
    Extract the object name from the link.

    Args:
        link (str): The MinIO URL/link containing the object name
            Example formats:
            - http://minio:9000/bucket-name/object-name
            - https://minio.example.com/bucket-name/object-name
            - http://localhost:9000/bucket-name/object-name?X-Amz-Algorithm=AWS4-HMAC-SHA256&...

    Returns:
        str: The extracted object name
    """
    # Remove query parameters if they exist
    base_url = link.split("?")[0]

    # Split the URL by '/' and get the last component
    parts = base_url.rstrip("/").split("/")

    # The object name is the last component
    object_name = parts[-1]

    return object_name
