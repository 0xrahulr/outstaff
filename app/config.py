import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

class BaseConfig:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-me")

    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{BASE_DIR / 'instance' / 'outstaff.db'}",
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_HTTPONLY = True
    WTF_CSRF_TIME_LIMIT = None
    SECURITY_PASSWORD_SALT = os.getenv("SECURITY_PASSWORD_SALT", "dev-password-salt")
