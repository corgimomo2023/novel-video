import hmac
import os
from fastapi import Cookie, HTTPException, Response, status
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

COOKIE_NAME = "video_session"
MAX_AGE = 60 * 60 * 24 * 7


def _serializer() -> URLSafeTimedSerializer:
    secret = os.environ.get("VIDEO_SESSION_SECRET", "")
    if len(secret) < 24:
        raise RuntimeError("VIDEO_SESSION_SECRET must be at least 24 characters")
    return URLSafeTimedSerializer(secret, salt="novel-video-session")


def authenticate(username: str, password: str) -> bool:
    expected_user = os.environ.get("VIDEO_ADMIN_USER", "alan")
    expected_password = os.environ.get("VIDEO_ADMIN_PASSWORD", "")
    return bool(expected_password) and hmac.compare_digest(username, expected_user) and hmac.compare_digest(password, expected_password)


def set_session(response: Response, username: str) -> None:
    response.set_cookie(COOKIE_NAME, _serializer().dumps({"username": username}), max_age=MAX_AGE,
                        httponly=True, secure=os.environ.get("VIDEO_COOKIE_SECURE", "true").lower() == "true",
                        samesite="strict", path="/")


def clear_session(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/")


def require_user(video_session: str | None = Cookie(default=None)) -> str:
    if not video_session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = _serializer().loads(video_session, max_age=MAX_AGE)
    except (BadSignature, SignatureExpired):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")
    return str(payload["username"])
