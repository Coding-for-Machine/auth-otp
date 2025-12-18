# bot/api.py
import time
from aiohttp import web
from pydantic import BaseModel, validator, ValidationError
from tortoise import Tortoise
from utils.cache import get_cache
from utils.database import Session, User
from decouple import config



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
    protected = {"/api/user", "/api/verify"}
    """
        Auth Middleware

        Bu middleware quyidagilarni bajaradi:

        1. Faqat `protected` ro‘yxatidagi routelarda token talab qilinadi.
        2. Request header-dan "Authorization" maydonini oladi.
        3. Agar token mavjud bo‘lmasa, 401 status bilan xato qaytaradi.
        4. Agar token noto‘g‘ri formatda bo‘lsa, 401 status bilan xato qaytaradi.
        5. Token orqali Session bazasidan foydalanuvchi sessiyasini tekshiradi.
        6. Agar token mos kelmasa, 401 status bilan xato qaytaradi.
        7. Foydalanuvchi sessiyasi topilsa, request obyektiga `user_id` qo‘shiladi.
        Shu bilan har bir endpoint ichida `request["user_id"]` orqali
        hozirgi foydalanuvchini aniqlash mumkin.
    """

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
    """
    Tizimga kirish uchin login qilganda foydalanovchidan
    faqat http request body uchin otp_code talab qilinadi!.
    otp_code --> bu string formatda va raqamlardan iborat
    masalan: "152535".
    opt_code uzinligi(length) 6 ta belgidan iborat bo'lish talab qilinadi.
    Json format:
        {
            "otp_code": "123456"
        }
    Http request:
        curl -X POST "http://localhost:8080/login" \
            -H "Content-Type: application/json" \
            -d '{"otp_code": "123456"}'
    """
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


    session = await Session.get_or_none(secret_key=data)
    if not session:
        return web.json_response({"error": "Invalid session"}, status=400)
    
    last_login_time = str(session.last_login)
    # Userni olish
    user = await User.get(id=session.user_id)

    return web.json_response({
        "token": session.jwt_token,
        "user": {
            "user_id": user.telegram_id,
            "username": user.username,
            "phone": user.phone,
            "full_name": user.full_name,
            "last_login": last_login_time,
        }
    })



async def get_user(request):
    """
    Foydalanavchi ma'lumotlarini olish uchin u ro'yxatddan o'tgan bo'lishi lozim.
    auth_middleware funksiyasi foydalanovchi jwt(json web token) ni tekshiradi.
    HTTP GET --> /api/user endpoint
    HTTP Response:
        {
            "user": {
                "full_name": "",
                "telegram_id": 0,
                "created_at": 2024-12-7 ...,
                "last_login": 2024-12-8 ...,
            }
        }
    """
    user = await User.get(id=request["user_id"])
    
    try:
        session = await user.session
        last_login_time = str(session.last_login)
    except:
        last_login_time = None

    return web.json_response({
        "user": {
            "user_id": user.telegram_id,
            "username": user.username,
            "phone": user.phone,
            "full_name": user.full_name,
            "last_login": last_login_time,
        }
    })

async def verify(request):
    
    return web.Response(status=200)  # middleware tekshiradi


app.add_routes([
    web.get("/", health_check),
    web.post("/api/login", otp_login),
    web.get("/api/user", get_user),
    web.get("/api/verify", verify),
])


import ssl

async def init_db():
    ssl_ctx = ssl.create_default_context()
    DB_HOST = config("HOST")
    BD_USER = config("BD_USER")
    DB_PASSWORD = config("PASSWORD")
    DB_DATABASE = config("DATABASE")
    await Tortoise.init(
        config={
            "connections": {
                "default": {
                    "engine": "tortoise.backends.asyncpg",
                    "credentials": {
                        "host": DB_HOST,
                        "port": 5432,
                        "user": BD_USER,
                        "password": DB_PASSWORD,
                        "database": DB_DATABASE,
                        "ssl": ssl_ctx,
                    },
                }
            },
            "apps": {
                "models": {
                    "models": ["utils.database"],
                    "default_connection": "default",
                }
            },
        }
    )

    await Tortoise.generate_schemas()
    print("PostgreSQL (Neon SSL) Ready")



if __name__ == "__main__":
    import asyncio
    asyncio.run(init_db())
    web.run_app(app, host="0.0.0.0", port=8080)
