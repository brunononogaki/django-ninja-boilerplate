# apps/core/schemas.py
from ninja import Schema


class StatusSchema(Schema):
    status: str