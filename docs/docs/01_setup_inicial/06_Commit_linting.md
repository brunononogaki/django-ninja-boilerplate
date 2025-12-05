# Commit Linting

Agora que o nosso CI está devidamente configurado, vamos começar a padronizar as nossas mensagens de Commit, e adicionar um commit linting no fluxo. Para isso, vamos usar a lib `commitizen` no projeto.

## Instalando o commitizen

Primeiramente, vamos adicionar o commitizen como uma dependência de desenvolvimento no projeto:
```bash
poetry add --dev commitizen
```

E agora configurar o Commitizen para usar as regras do [`conventional-commits`](https://www.conventionalcommits.org/en/v1.0.0/). Lá no `pyproject.toml`, adicionaremos o seguinte

```toml title="./pyproject.toml"
[tool.commitizen]
name = "cz_conventional_commits"
```

## Instalando o pre-commit
poetry add --group dev pre-commit