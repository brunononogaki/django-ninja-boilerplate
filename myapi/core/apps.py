from decouple import config
from django.apps import AppConfig
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models.signals import post_migrate
from loguru import logger


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'myapi.core'

    def ready(self):
        logger.info('✅ CoreConfig.ready() was called!')
        # Register the signal handler for post_migrate
        post_migrate.connect(self.create_default_superuser, sender=self)

    @staticmethod
    def create_default_superuser(sender, **kwargs):
        """Create or update the default superuser after migrations run."""
        logger.info('🔄 post_migrate signal triggered - attempting to create superuser...')
        User = get_user_model()
        username = config('DJANGO_ADMIN_USER', default='admin')
        email = config('DJANGO_ADMIN_EMAIL', default='admin@admin.com')
        password = config('DJANGO_ADMIN_PASSWORD', default='devpassword')

        try:
            logger.info(f'📝 Creating/updating superuser: {username}')
            existing = User.objects.filter(username=username).first()
            if existing:
                logger.info(f'✏️ User {username} already exists, checking for updates...')
                changed = False
                if not existing.is_superuser:
                    existing.is_superuser = True
                    changed = True
                if not existing.is_staff:
                    existing.is_staff = True
                    changed = True
                if email and getattr(existing, 'email', None) != email:
                    existing.email = email
                    changed = True
                if password:
                    try:
                        validate_password(password, user=existing)
                    except DjangoValidationError as e:
                        logger.warning(f'⚠️ Superuser password does not meet validators: {e.messages}')
                    existing.set_password(password)
                    changed = True
                if changed:
                    existing.save()
                    logger.info(f'✅ User {username} updated!')
                else:
                    logger.info(f'ℹ️ User {username} already has correct settings')
            else:
                # create_superuser will set is_superuser and is_staff
                User.objects.create_superuser(username=username, email=email, password=password)
                logger.info(f'✅ Superuser {username} created!')
        except Exception as e:
            # Don't raise during startup; fail silently to avoid breaking deploys.
            logger.error(f'❌ Error creating superuser: {type(e).__name__}: {str(e)}')
