"""
Adaptadores customizados para django-allauth
Fornece funcionalidades extras para OAuth e gestão de contas
"""

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    """Adaptador customizado para contas sociais (Google, etc)"""

    def pre_social_login(self, request, sociallogin):  # noqa: PLR6301
        picture = sociallogin.account.extra_data.get('picture')
        user = sociallogin.user
        if picture and user and user.pk and user.avatar_url != picture:
            user.avatar_url = picture
            user.save(update_fields=['avatar_url'])

    def populate_user(self, request, sociallogin, data):
        """
        Preenche os dados do usuário a partir dos dados do provider social
        """
        user = super().populate_user(request, sociallogin, data)

        # Garante que username seja sempre o email
        if user.email:
            user.username = user.email

        picture = sociallogin.account.extra_data.get('picture')
        if picture:
            user.avatar_url = picture

        return user
