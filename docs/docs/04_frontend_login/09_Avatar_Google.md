# Exibindo o Avatar do Google no Perfil do Usuário

Quando o usuário faz login via Google, o `django-allauth` recebe os dados do perfil (nome, email, foto de perfil) e os armazena em `SocialAccount.extra_data`. Vamos aproveitar esse dado para exibir o avatar do Google na tela de perfil.

## O que precisa ser feito

1. Adicionar o campo `avatar_url` no model `UUIDUser`
2. Criar a migração
3. Atualizar o adapter para salvar a foto do Google no campo
4. Expor o campo no schema da API
5. Exibir a imagem no frontend

## 1. Adicionando o campo no model

```python title="./myapi/users/models.py" hl_lines="4"
class UUIDUser(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    avatar_url = models.URLField(null=True, blank=True)

    def __str__(self):
        return self.username
```

## 2. Criando a migração

```bash
python manage.py makemigrations users
python manage.py migrate
```

## 3. Salvando o avatar no adapter

O `extra_data` retornado pelo Google inclui um campo `picture` com a URL da foto de perfil. Precisamos salvá-lo em dois momentos distintos:

**Na criação de novos usuários** — via `populate_user`, chamado apenas no primeiro cadastro social:

```python title="./myapi/core/adapters.py" hl_lines="10-12"
def populate_user(self, request, sociallogin, data):
    user = super().populate_user(request, sociallogin, data)

    # Garante que username seja sempre o email
    if user.email:
        user.username = user.email

    # Salva a foto de perfil do Google
    picture = sociallogin.account.extra_data.get('picture')
    if picture:
        user.avatar_url = picture

    return user
```

**Em todos os logins** — via `pre_social_login`, que roda sempre que o usuário autentica via Google. Isso garante que usuários já existentes também tenham o avatar salvo:

```python title="./myapi/core/adapters.py" hl_lines="3-6"
def pre_social_login(self, request, sociallogin):
    picture = sociallogin.account.extra_data.get('picture')
    user = sociallogin.user
    if picture and user and user.pk and user.avatar_url != picture:
        user.avatar_url = picture
        user.save(update_fields=['avatar_url'])
```

!!! tip

    O `pre_social_login` só faz o `save` se o avatar mudou (`user.avatar_url != picture`), evitando um write desnecessário no banco a cada login.

## 4. Expondo o campo no schema

Adicione `avatar_url` na lista de campos do `UserWithGroupsSchema`:

```python title="./myapi/users/schemas.py" hl_lines="5"
UserWithGroupsSchema = create_schema(
    User,
    depth=1,
    fields=['id', 'username', 'first_name', 'last_name', 'email', 'is_active', 'groups', 'avatar_url'],
    custom_fields=[('get_full_name', str, None)],
)
```

## 5. Exibindo no frontend

Na tela de perfil (`home.jsx`), exibimos a imagem quando `avatar_url` estiver preenchido, e as iniciais do nome como fallback:

```jsx title="./next/pages/home.jsx"
<div className="w-14 h-14 rounded-2xl flex-shrink-0 overflow-hidden"
  style={!user?.avatar_url ? { background: "linear-gradient(135deg, #6366f1, #8b5cf6)" } : {}}>
  {user?.avatar_url ? (
    <img
      src={user.avatar_url}
      alt={displayName}
      className="w-full h-full object-cover"
      referrerPolicy="no-referrer"
    />
  ) : (
    <div className="w-full h-full flex items-center justify-center text-white font-bold text-lg">
      {initials}
    </div>
  )}
</div>
```

!!! tip

    O atributo `referrerPolicy="no-referrer"` é necessário para que o browser consiga carregar as imagens hospedadas nos servidores do Google (`lh3.googleusercontent.com`), que por padrão bloqueiam requisições sem esse header.

!!! note

    O campo `avatar_url` fica `null` para usuários que se cadastraram via email/senha. O fallback com iniciais garante que esses usuários continuem tendo uma representação visual no perfil.
