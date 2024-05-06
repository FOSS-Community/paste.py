import random
import string
import os
import re
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


def _find_without_extension(file_name: str) -> str:
    file_list: list = os.listdir("data")
    pattern_with_dot: Pattern[str] = re.compile(
        r"^(" + re.escape(file_name) + r")\.")
    pattern_without_dot: Pattern[str] = re.compile(
        r"^" + file_name + "$")
    math_pattern: list = [
        x for x in file_list if pattern_with_dot.match(x) or pattern_without_dot.match(x)]
    if len(math_pattern) == 0:
        return str()
    else:
        return math_pattern[0]
