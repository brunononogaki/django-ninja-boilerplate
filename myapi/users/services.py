from datetime import timedelta

from decouple import config
from django.contrib.auth import get_user_model
from django.utils import timezone
from loguru import logger

from infra.mailer import send_message

from ..core.exceptions import ServiceError, ValidationError
from .models import ActivationToken, PasswordResetToken

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
        raise ServiceError('An error ocurred when sending the e-mail')


def verify_activation_token(token_id: str, is_resend: bool = False):
    """
    Verify activation token.

    Args:
        token_id: Activation token ID (UUID)
        is_resend: Check if this is a request for a new token or resend an expired one

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
        logger.warning(f'Attempt to activate user with invalid token: token_id={token_id}')
        raise ValidationError('Activation token not found')

    # Get the associated user
    user = activation_token.user

    # Check if user is already active
    if user.is_active:
        logger.warning(f'Attempt to resend activation for already active user: {user.username}')
        raise ValidationError('User account is already activated')

    # If requesting a new token, we don't need to check if it is expired or used, just return the user
    if is_resend:
        # Check if token is expired
        if timezone.now() < activation_token.expires_at:
            logger.warning(f'Attempt to resend activation with valid token: token_id={token_id}')
            raise ValidationError('Token is still valid. Use the existing link to activate your account')
        return user

    else:
        # Check if token is expired
        if timezone.now() > activation_token.expires_at:
            logger.warning(f'Activation token is expired: token_id={token_id}')
            raise ValidationError('This link is expired, please request a new one')

        # Check if token is already used
        if activation_token.used_at is not None:
            logger.warning(f'Activation token already used for user {activation_token.user_id}')
            return activation_token.user

    # Activate user
    user.is_active = True
    user.save()

    # Mark token as used
    activation_token.used_at = timezone.now()
    activation_token.save()

    logger.info(f'User {user.username} activated')
    return user


def send_password_reset_email(user, token_expiry_minutes=15):
    """
    Send password reset email to user with link to reset password.

    Args:
        user: User instance
        token_expiry_minutes: Number of minutes until token expires (default: 15)
    """
    # Get frontend domain from env
    frontend_fqdn = config('FRONTEND_FQDN', default='localhost:3000')

    # Determine protocol based on domain
    use_https = 'localhost' not in frontend_fqdn
    protocol = 'https' if use_https else 'http'

    # Create password reset token record (id is the token)
    expires_at = timezone.now() + timedelta(minutes=token_expiry_minutes)
    reset_token = PasswordResetToken.objects.create(
        user=user,
        expires_at=expires_at,
    )

    # Build password reset URL using the token id
    reset_url = f'{protocol}://{frontend_fqdn}/reset-password/{reset_token.id}'

    # Prepare email with HTML formatting
    html_body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto;">
                <h2>Redefinir Senha</h2>
                <p>Olá <strong>{user.first_name or user.username}</strong>,</p>
                <p>Recebemos uma solicitação para redefinir sua senha. Clique no link abaixo:</p>
                <p style="text-align: center; margin: 30px 0;">
                    <a href="{reset_url}" style="background-color: #28a745; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block;">
                        Redefinir Senha
                    </a>
                </p>
                <p style="font-size: 14px; color: #666;">
                    Ou copie este link no seu navegador:<br>
                    <code style="background-color: #f4f4f4; padding: 5px; border-radius: 3px; word-break: break-all;">
                        {reset_url}
                    </code>
                </p>
                <p style="font-size: 12px; color: #999;">
                    Este link expira em <strong>{token_expiry_minutes} minutos</strong>.
                </p>
                <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                <p style="font-size: 12px; color: #999;">
                    Se você não solicitou esta redefinição, ignore este email.
                </p>
                <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; text-align: center;">
                    <p style="font-size: 12px; color: #666; margin: 5px 0;">
                        <strong>Equipe Django Ninja API Boilerplate</strong><br>
                        Email: <a href="mailto:djangoninja.api@gmail.com" style="color: #28a745; text-decoration: none;">djangoninja.api@gmail.com</a>
                    </p>
                </div>
            </div>
        </body>
    </html>
    """

    # Prepare email
    mail_options = {
        'subject': 'Redefinir sua senha',
        'body': html_body,
        'from': 'contato@myapi.com',
        'to': [user.email],
    }

    try:
        send_message(mail_options)
        logger.info(f'Password reset email sent to {user.email}')
    except Exception as e:
        logger.error(f'Error sending password reset email to {user.email}: {e}')
        raise ServiceError('An error ocurred when sending the e-mail')


def confirm_password_reset_token(token_id: str):
    """
    Verify password reset token, mark it as used, and return the associated user.

    Raises ValidationError if token is not found, expired, or already used.
    """
    try:
        password_reset_token = PasswordResetToken.objects.get(id=token_id)
    except PasswordResetToken.DoesNotExist:
        logger.warning(f'Attempt to change password with invalid token: token_id={token_id}')
        raise ValidationError('Password reset token not found')

    user = password_reset_token.user

    if timezone.now() > password_reset_token.expires_at:
        logger.warning(f'Password reset token is expired: token_id={token_id}')
        raise ValidationError('This link is expired, please request a new one')

    if password_reset_token.used_at is not None:
        logger.warning(f'Password reset token already used for user {password_reset_token.user_id}')
        raise ValidationError('This link was already used, please request a new one')

    password_reset_token.used_at = timezone.now()
    password_reset_token.save()

    return user


def validate_password_reset_token(token_id: str):
    """
    Validate password reset token without marking it as used.

    Args:
        token_id: Password reset token ID (UUID)

    Returns:
        Dictionary with validation result: {valid: bool, message: str}
    """
    try:
        reset_token = PasswordResetToken.objects.get(id=token_id)
    except PasswordResetToken.DoesNotExist:
        logger.warning(f'Attempt to validate non-existent token: token_id={token_id}')
        return {'valid': False, 'message': 'Token not found'}

    # Check if token is expired
    if timezone.now() > reset_token.expires_at:
        logger.warning(f'Attempt to validate expired token: token_id={token_id}')
        return {'valid': False, 'message': 'Token has expired'}

    # Check if token is already used
    if reset_token.used_at is not None:
        logger.warning(f'Attempt to validate already used token: token_id={token_id}')
        return {'valid': False, 'message': 'Token has already been used'}

    logger.info(f'Token validation successful: token_id={token_id}')
    return {'valid': True, 'message': 'Token is valid'}
