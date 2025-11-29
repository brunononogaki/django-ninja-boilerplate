from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'myapi.core'

    def ready(self):
        # Create/update default superuser after migrations run.
        # Keep imports local to avoid side-effects during Django startup.
        from decouple import config
        from django.contrib.auth import get_user_model
        from django.db.models.signals import post_migrate

        def create_default_superuser(sender, **kwargs):
            User = get_user_model()
            username = config('DJANGO_ADMIN_USER', default='admin')
            email = config('DJANGO_ADMIN_EMAIL', default='admin@admin.com')
            password = config('DJANGO_ADMIN_PASSWORD', default='devpassword')

            try:
                existing = User.objects.filter(username=username).first()
                if existing:
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
                        existing.set_password(password)
                        changed = True
                    if changed:
                        existing.save()
                else:
                    # create_superuser will set is_superuser and is_staff
                    User.objects.create_superuser(username=username, email=email, password=password)
            except Exception:
                # Don't raise during migrate; fail silently to avoid breaking deploys.
                pass

        post_migrate.connect(create_default_superuser, sender=self)
