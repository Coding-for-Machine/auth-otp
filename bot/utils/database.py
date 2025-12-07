from tortoise import fields, models

class User(models.Model):
    id = fields.BigIntField(pk=True)
    username = fields.CharField(max_length=150, unique=True)
    telegram_id = fields.BigIntField(unique=True, null=True)
    phone = fields.CharField(max_length=20, null=True)
    full_name = fields.CharField(max_length=500, null=True)

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "users"


class Session(models.Model):
    id = fields.BigIntField(pk=True)
    user = fields.OneToOneField("models.User", related_name="sessions", on_delete=fields.CASCADE)
    secret_key = fields.CharField(max_length=150, null=True)
    jwt_token = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    last_login = fields.DatetimeField(auto_now=True)
    expires_at = fields.DatetimeField(null=True)

    class Meta:
        table = "sessions"