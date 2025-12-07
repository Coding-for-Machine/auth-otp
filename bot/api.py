# bot/api.py
import time
from aiohttp import web
from pydantic import BaseModel, validator, ValidationError
from tortoise import Tortoise
from utils.cache import get_cache
from utils.database import Session, User


# CORS Middleware
@web.middleware
async def cors_middleware(request, handler):
    if request.method == "OPTIONS":
        return web.Response(headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
        })

    response = await handler(request)
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response


# Auth Middleware
@web.middleware
async def auth_middleware(request, handler):
    protected = {"/api/user"}  # faqat token talab qilinadigan routelar

    if request.path in protected:
        auth = request.headers.get("Authorization")
        if not auth:
            return web.json_response({"error": "Token required"}, status=401)

        parts = auth.split(" ")
        if len(parts) != 2:
            return web.json_response({"error": "Invalid Authorization format"}, status=401)

        token = parts[1]
        session = await Session.get_or_none(jwt_token=token)
        if not session:
            return web.json_response({"error": "Invalid token"}, status=401)

        request["user_id"] = session.user_id

    return await handler(request)


# ===== Request Schemas =====
class OTPSchema(BaseModel):
    otp_code: str

    @validator("otp_code")
    def otp_must_be_six_digits(cls, v):
        if not v.isdigit() or len(v) != 6:
            raise ValueError("OTP 6 xonali bo‘lishi kerak")
        return v


#  App 
app = web.Application(middlewares=[cors_middleware, auth_middleware])


#  health 
async def health_check(request):
    return web.json_response({"status": "ok"})


async def otp_login(request):
    try:
        payload = OTPSchema(**await request.json())
    except ValidationError as e:
        return web.json_response({"error": str(e)}, status=400)

    otp = payload.otp_code

    # Cache dan olish
    data, expire_at = get_cache(otp)

    # Agar cache bo'lmasa yoki muddati o'tgan bo'lsa
    if data is None or expire_at is None or expire_at < time.time():
        return web.json_response({"error": "OTP expired or invalid"}, status=400)

    # Sessionni topamiz
    session = await Session.get_or_none(secret_key=data)
    if not session:
        return web.json_response({"error": "Invalid session"}, status=400)

    return web.json_response({"token": session.jwt_token})




async def get_user(request):
    user = await User.get(id=request["user_id"])
    session = await Session.get_or_none(user_id=user.id)  # oxirgi session

    last_login_time = str(session.last_login) if session else None

    return web.json_response({
        "user": {
            "full_name": user.full_name,
            "telegram_id": user.telegram_id,
            "created_at": str(user.created_at),
            "last_login": last_login_time,
        },
        "stats": {"active": True}
    })


async def verify(request):
    return web.Response(status=200)  # middleware tekshiradi


app.add_routes([
    web.get("/", health_check),
    web.post("/login", otp_login),
    web.get("/api/user", get_user),
    web.get("/verify", verify),
])


async def init_db():
    await Tortoise.init(
        db_url="sqlite://bot_database.sqlite3",
        modules={"models": ["utils.database"]},
    )
    await Tortoise.generate_schemas()
    print("SQLite Ready")


if __name__ == "__main__":
    import asyncio
    asyncio.run(init_db())
    web.run_app(app, host="0.0.0.0", port=8080)
