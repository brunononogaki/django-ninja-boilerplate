from ninja import Schema


class StatusSchema(Schema):
    updated_at: str
    db_version: str
    max_connections: int
    active_connections: int


class TokenResponse(Schema):
    access_token: str
    refresh_token: str | None = None
    token_type: str = 'bearer'
