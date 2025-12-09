# Django Ninja Boilerplate

Bem-vindo ao **Django Ninja Boilerplate**!
Estou construindo esse projeto do absoluto **ZERO**, desde a criação do ambiente, até termos uma API funcional desenvolvida com Django Ninja e um Frontend em Next.js consumindo a API. E a ideia é eu documentar cada etapa desse processo, e me auxiliar no estudo e progresso nesse Framework. Ainda está em construção, então faltam muitas coisas... mas vamos evoluindo pouco a pouco.

## Recursos disponíveis até o momento:

- Django 5.x + Django Ninja (Backend)
- Next.js 16.x (Frontend)
- Autenticação JWT 
- Model de Users customizado com UUID
- CRUD de Usuários
- Testes automatizados do Backend com Pytest
- Deploy Automatizado com GitHub Actions em um servidor VPS da Hostinger.
- Documentação da API com Swagger/OpenAPI

## Como começar

1. **Clone o projeto**
	```sh
	git clone https://github.com/seu-usuario/django-ninja-boilerplate.git
	cd django-ninja-boilerplate
	```

2. **Configuração local**
	- Ajuste o arquivo `.env.development` com as configurações do seu ambiente
	- Instale as dependências:
	  ```sh
	  poetry install
	  ```

3. **Rodando localmente**
	```sh
	poetry run task run
	```

4. **Acesse a documentação**
	- Swagger: [http://localhost:8000/api/docs](http://localhost:8000/api/docs)

## Deploy

- Deploy em produção é feito via GitHub Actions em uma VPS da Hostinger

## Testes

```sh
poetry run task test
```


---

Autor: Bruno Nonogaki  
[LinkedIn](https://www.linkedin.com/in/brunono/)
