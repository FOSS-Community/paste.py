import random
import string
import os
from pathlib import Path


def generate_uuid() -> str:
    # Combine uppercase letters, lowercase letters, and digits
    characters: str = string.ascii_letters + string.digits

    # Generate a random 4-character code
    random_code: str = "".join(random.choice(characters) for _ in range(4))

    return random_code


def extract_extension(file_name: Path) -> str:
    _, extension = os.path.splitext(file_name)
    return extension
