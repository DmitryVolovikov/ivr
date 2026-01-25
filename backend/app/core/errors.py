from dataclasses import dataclass


@dataclass
class AuthError(Exception):
    status_code: int
    error_code: str
    detail: str
