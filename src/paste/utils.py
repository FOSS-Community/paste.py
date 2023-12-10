import random
import string
import os

def generate_uuid():
    # Combine uppercase letters, lowercase letters, and digits
    characters = string.ascii_letters + string.digits

    # Generate a random 4-character code
    random_code = ''.join(random.choice(characters) for _ in range(4))

    return random_code

def extract_extension(file_name):
    _, extension = os.path.splitext(file_name)
    return extension

print(extract_extension("file.txt"))