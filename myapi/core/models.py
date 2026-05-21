from datetime import datetime, timezone

from django.db import models


class RefreshTokenDenylist(models.Model):
    jti = models.UUIDField(unique=True, db_index=True)
    expires_at = models.DateTimeField()

    class Meta:
        indexes = [models.Index(fields=['expires_at'])]

    @classmethod
    def cleanup_expired(cls):
        cls.objects.filter(expires_at__lt=datetime.now(tz=timezone.utc)).delete()
