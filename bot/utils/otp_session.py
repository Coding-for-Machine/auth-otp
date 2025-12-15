# bot/utils/otp_session.py
import pyotp
import time
from utils.cache import get_cache, set_cache
from utils.jwt_ import create_token
from utils.database import User, Session

async def create_or_get_session(user_id: int, phone: str):
    user = await User.get_or_none(telegram_id=user_id)
    if not user:
        return None, None, None, False

    session = await Session.get_or_none(user_id=user.id)

    # Cache tekshiruvi
    otp_code, expire_at = get_cache(user_id)
    if otp_code and expire_at and expire_at > time.time():
        # Eskirmagan OTP mavjud
        return user, otp_code, session.jwt_token if session else None, True

    secret = pyotp.random_base32() if not session else session.secret_key or pyotp.random_base32()
    # Yangi OTP yaratish
    totp = pyotp.TOTP(secret, interval=60)
    otp_code = totp.now()

    # JWT yaratish
    jwt_token = create_token(
        session_id=session.id if session else 0,
        user_id=user_id,
        phone_number=phone,
        username=user.username,
        full_name=user.full_name,
        secret_key=secret
    )

    if session:
        session.secret_key = secret
        session.jwt_token = jwt_token
        await session.save()
    else:
        session = await Session.create(
            user_id=user.id,
            secret_key=secret,
            jwt_token=jwt_token
        )

    set_cache(otp_code, secret, cache_time=60)
    set_cache(user_id, otp_code, cache_time=60)
    return user, otp_code, jwt_token, False
