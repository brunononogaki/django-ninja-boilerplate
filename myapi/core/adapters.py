"""
Adaptadores customizados para django-allauth
Fornece funcionalidades extras para OAuth e gestão de contas
"""

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    """Adaptador customizado para contas sociais (Google, etc)"""

    def pre_social_login(self, request, sociallogin):
        """
        Chamado antes do login social
        """
        pass

    def populate_user(self, request, sociallogin, data):
        """
        Preenche os dados do usuário a partir dos dados do provider social
        """
        user = super().populate_user(request, sociallogin, data)

        # Garante que username seja sempre o email
        if user.email:
            user.username = user.email

        return user
