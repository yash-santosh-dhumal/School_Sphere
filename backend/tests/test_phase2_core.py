import pytest
from app.core.security import verify_password, hash_password, create_access_token
from jose import jwt
from app.core.config import get_settings
import os
os.environ["JWT_SECRET_KEY"] = "test-secret-key-must-be-at-least-32-characters-long"
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["APP_ENV"] = "test"

def test_password_hashing():
    password = "supersecretpassword123!"
    hashed = hash_password(password)
    
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("wrongpassword", hashed) is False

def test_create_access_token():
    subject = "user123"
    token = create_access_token(subject)
    
    # decode the token to verify its contents
    settings = get_settings()
    payload = jwt.decode(token, settings.jwt_secret_key.get_secret_value(), algorithms=["HS256"])
    
    assert payload["sub"] == subject
    assert "exp" in payload
