import random
import string
import os
import sys


def generate_uuid() -> str:
    # Combine uppercase letters, lowercase letters, and digits
    characters = string.ascii_letters + string.digits

    # Generate a random 4-character code
    random_code = ''.join(random.choice(characters) for _ in range(4))

    return random_code


def extract_extension(file_name) -> str:
    _, extension = os.path.splitext(file_name)
    return extension


def check_file_size_limit(file) -> bool:
    # Check if the file size is less than 20 MB -> true else false
    if sys.getsizeof(file) < 20_000_000:
        return True
    return False
