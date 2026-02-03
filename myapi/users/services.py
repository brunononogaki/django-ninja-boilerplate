from datetime import timedelta

from decouple import config
from django.contrib.auth import get_user_model
from django.utils import timezone
from loguru import logger

from infra.mailer import send_message

from .models import ActivationToken

User = get_user_model()


def send_activation_email(user, token_expiry_minutes=15):
    """
    Send activation email to user with link to activate account.

    Args:
        user: User instance
        token_expiry_minutes: Number of minutes until token expires (default: 15)
    """
    # Get frontend domain from env
    frontend_fqdn = config('FRONTEND_FQDN', default='localhost:3000')

    # Determine protocol based on domain
    use_https = 'localhost' not in frontend_fqdn
    protocol = 'https' if use_https else 'http'

    # Create activation token record (id is the token)
    expires_at = timezone.now() + timedelta(minutes=token_expiry_minutes)
    activation_token = ActivationToken.objects.create(
        user=user,
        expires_at=expires_at,
    )

    # Build activation URL using the token id
    activation_url = f'{protocol}://{frontend_fqdn}/activate/{activation_token.id}'

    # Prepare email with HTML formatting
    html_body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto;">
                <h2>Bem-vindo!</h2>
                <p>Olá <strong>{user.first_name or user.username}</strong>,</p>
                <p>Clique no link abaixo para ativar sua conta:</p>
                <p style="text-align: center; margin: 30px 0;">
                    <a href="{activation_url}" style="background-color: #007bff; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block;">
                        Ativar Conta
                    </a>
                </p>
                <p style="font-size: 14px; color: #666;">
                    Ou copie este link no seu navegador:<br>
                    <code style="background-color: #f4f4f4; padding: 5px; border-radius: 3px; word-break: break-all;">
                        {activation_url}
                    </code>
                </p>
                <p style="font-size: 12px; color: #999;">
                    Este link expira em <strong>{token_expiry_minutes} minutos</strong>.
                </p>
                <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                <p style="font-size: 12px; color: #999;">
                    Se você não criou essa conta, ignore este email.
                </p>
                <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; text-align: center;">
                    <p style="font-size: 12px; color: #666; margin: 5px 0;">
                        <strong>Equipe Django Ninja API Boilerplate</strong><br>
                        Email: <a href="mailto:djangoninja.api@gmail.com" style="color: #007bff; text-decoration: none;">djangoninja.api@gmail.com</a>
                    </p>
                </div>
            </div>
        </body>
    </html>
    """

    # Prepare email
    mail_options = {
        'subject': 'Ative sua conta',
        'body': html_body,
        'from': 'contato@myapi.com',
        'to': [user.email],
    }

    try:
        send_message(mail_options)
        logger.info(f'Activation email sent to {user.email}')
    except Exception as e:
        logger.error(f'Error sending activation email to {user.email}: {e}')
        raise


def verify_activation_token(token_id: str):
    """
    Verify activation token.

    Args:
        token_id: Activation token ID (UUID)

    Returns:
        User instance if token is valid and not expired
        None if token is invalid, expired, or already used
    """
    try:
        # Find activation token by id
        activation_token = ActivationToken.objects.get(
            id=token_id,
        )
    except ActivationToken.DoesNotExist:
        logger.warning(f'Invalid activation token: token_id={token_id}')
        return None

    # Check if token is expired
    if timezone.now() > activation_token.expires_at:
        logger.warning(f'Activation token expired for user {activation_token.user_id}')
        return None

    # Check if token is already used
    if activation_token.used_at is not None:
        logger.warning(f'Activation token already used for user {activation_token.user_id}')
        return None

    # Activate user
    user = activation_token.user
    user.is_active = True
    user.save()

    # Mark token as used
    activation_token.used_at = timezone.now()
    activation_token.save()

    logger.info(f'User {user.username} activated')
    return user
