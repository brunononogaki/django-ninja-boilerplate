from ninja import Schema


class StatusSchema(Schema):
    updated_at: str
    db_version: str
    max_connections: int
    active_connections: int


class LoginRequest(Schema):
    username: str
    password: str


class MessageSchema(Schema):
    message: str
