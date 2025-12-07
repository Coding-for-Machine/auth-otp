import jwt
import datetime
from decouple import config

# with open("private.pem", "r") as f:
#     SECRET_KEY = f.read()

# with open("public.pem", "r") as f:
#     PUBLIC_KEY = f.read()

SECRET_KEY = config("SECRET_KEY")

def create_token(
    session_id: int,
    user_id: int,
    phone_number: str,
    username: str = "",
    full_name: str = "",
    secret_key: str = ""
):
    payload = {
        "session_id": session_id,
        "telegram_id": user_id,
        "phone_number": phone_number,
        "username": username,
        "full_name": full_name,
        "secret_key": secret_key,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=356),
        "iat": datetime.datetime.utcnow()
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")  # RSA
    return token


def verify_token(token: str):
    try:
        data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return data
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
