from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel


class UserRole(str, Enum):
    ADMIN = "Admin"
    ACCOUNTANT = "Accountant"


class User(BaseModel):
    username: str
    password_hash: str
    role: UserRole

    def verify_password(self, password: str) -> bool:
        from ggs_accounting.utils import verify_password

        return verify_password(password, self.password_hash)
