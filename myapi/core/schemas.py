from ninja import Schema


class StatusSchema(Schema):
    updated_at: str
    db_version: str
    max_connections: int
    active_connections: int


class LoginRequest(Schema):
    username: str
    password: str


class RefreshRequest(Schema):
    refresh_token: str


class TokenResponse(Schema):
    access_token: str
    refresh_token: str | None = None
    token_type: str = 'bearer'
