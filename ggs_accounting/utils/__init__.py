import hashlib


def camel_case(text: str) -> str:
    """Convert a string to camel case words."""
    return " ".join(word.capitalize() for word in text.split())


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed

from .helpers import *
