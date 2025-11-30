# Django Ninja Boilerplate

Bem-vindo ao **Django Ninja Boilerplate**!
Estou constuindo essa API do absoluto ZERO, desde a criação do ambiente até termos uma API funcional de um projeto real. E a ideia é eu documentar cada etapa desse processo, e me auxiliar no estudo e progresso nesse Framework. Ainda está em construção, então faltam muitas coisas... mas vamos fazendo pouco a pouco.

## Recursos principais

- Django 5.x + Django Ninja (API moderna e tipada)
- Autenticação JWT nativa (login, refresh, proteção de rotas)
- Usuário customizado com UUID
- CRUD de Usuários
- Testes automatizados com pytest
- Deploy Automatizado com GitHub Actions em um servidor VPS da Hostinger.
- Documentação automática via Swagger/OpenAPI

## Como começar

1. **Clone o projeto**
	```sh
	git clone https://github.com/seu-usuario/django-ninja-boilerplate.git
	cd django-ninja-boilerplate
	```

2. **Configuração local**
	- Copie `.env.example` para `.env.development` e ajuste as variáveis.
	- Instale as dependências:
	  ```sh
	  poetry install
	  ```

3. **Rodando localmente**
	```sh
	poetry run python manage.py migrate
	poetry run python manage.py createsuperuser
	poetry run task run
	```

4. **Acesse a documentação**
	- Swagger: [http://localhost:8000/api/docs](http://localhost:8000/api/docs)

## Deploy

- Pronto para deploy via Docker e GitHub Actions.
- Veja o arquivo `README.md` e a documentação para detalhes.

## Testes

```sh
poetry run task test
```


---

Autor: Bruno Nonogaki  
[LinkedIn](https://www.linkedin.com/in/brunono/)
