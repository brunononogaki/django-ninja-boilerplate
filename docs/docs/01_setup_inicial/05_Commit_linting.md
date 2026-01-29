# Commit Linting

Agora que o nosso CI está devidamente configurado, vamos começar a padronizar as nossas mensagens de Commit, e adicionar um commit linting no fluxo. Para isso, vamos usar a biblioteca `pre-commit`, que é responsável por gerenciar Hooks do Git. Com ela, poderemos configurar o nosso ambiente local de desenvolvimento para chamar o `commitizen` e validar se as nossas mensagens de commit seguem um padrão estabelecido pelo [`conventional-commits`](https://www.conventionalcommits.org/en/v1.0.0/).

## Instalando o pre-commit

A instalação será feita via `poetry` como uma dependência de `dev`:
```bash
poetry add --group dev pre-commit
```

Agora, vamos criar um arquivo chamado `.pre-commit-config.yaml` na raíz do projeto:
```yaml title="./.pre-commit-config.yaml"
repos:
  - repo: https://github.com/commitizen-tools/commitizen
    rev: v3.12.0
    hooks:
      - id: commitizen
        stages: [commit-msg]
```

Agora quando fizermos um commit, o fluxo será:

  1. Você tenta fazer git commit
  2. O hook do pre-commit/commitizen é acionado automaticamente
  3. Se a mensagem não seguir o padrão convencional, o commit é bloqueado
  4. Você ajusta a mensagem e tenta novamente


!!! success

    Agora, sempre que fizermos um commit novo, validaremos se a mensagem está no padrão. Por exemplo:
    ```bash
    git commit -m "teste"              
    commitizen check.........................................................Failed
    - hook id: commitizen
    - exit code: 14

    commit validation: failed!
    please enter a commit message in the commitizen format.
    commit "": "teste"
    pattern: (?s)(build|ci|docs|feat|fix|perf|refactor|style|test|chore|revert|bump)(\(\S+\))?!?:( [^\n\r]+)((\n\n.*)|(\s*))?$
    ```

## Instalando o commitizen

Opcionalmente, podemos instalar o `commitizen`, para ele dar pra gente uma espécie de formulário para preenchermos na hora de fazer o commit, o que pode nos ajudar na seleção de um type, por exemplo. Para isso, vamos instalar o `commitizen` como uma dependência de dev:

```bash
poetry add --group dev commitizen
```

E no arquivo `pyproject.toml`, adicionaremos essas configurações:

```toml title="./pyproject.toml"
[tool.commitizen]
name = "cz_conventional_commits"
```

E para facilitar, vamos criar um atalho do Taskipy para o comando `commit`:
```toml title="./pyproject.toml" hl_lines="14"
[tool.taskipy.tasks]
services-up = "docker compose -f infra/compose-dev.yaml up -d"
services-stop = "docker compose -f infra/compose-dev.yaml stop"
services-down = "docker compose -f infra/compose-dev.yaml down"
create-env-dev = "ln -sf .env.development .env"
create-env-prod = "ln -sf .env.production .env"
run = 'task create-env-dev && task services-up && python infra/wait-for-postgres.py && python manage.py migrate && python manage.py runserver'
down = "pkill -f 'manage.py runserver'; docker compose -f infra/compose-dev.yaml down"
test = 'task create-env-dev && task services-up && python infra/wait-for-postgres.py && honcho start web test'
test-watch = 'pytest-watch'
lint = 'ruff check'
format = 'ruff format '
migrate = 'python manage.py makemigrations && python manage.py migrate'
commit = 'poetry run cz commit'
```

Agora quando dermos o comando `task commit`, o Commitizen será chamado para nos dar um formulário de commit:
```bash
? Select the type of change you are committing (Use arrow keys)
 » fix: A bug fix. Correlates with PATCH in SemVer
   feat: A new feature. Correlates with MINOR in SemVer
   docs: Documentation only changes
   style: Changes that do not affect the meaning of the code (white-space, formatting, missing semi-colons, etc)
   refactor: A code change that neither fixes a bug nor adds a feature
   perf: A code change that improves performance
   test: Adding missing or correcting existing tests
   build: Changes that affect the build system or external dependencies (example scopes: pip, docker, npm)
   ci: Changes to CI configuration files and scripts (example scopes: GitLabCI)
   
? Select the type of change you are committing ci: Changes to CI configuration files and scripts (example scopes: GitLabCI)
? What is the scope of this change? (class or file name): (press [enter] to skip)
 
? Write a short and imperative summary of the code changes: (lower case and no period)
 add commitizen to the project and add task commit shortcut in taskipy config
? Provide additional contextual information about the code changes: (press [enter] to skip)
 
? Is this a BREAKING CHANGE? Correlates with MAJOR in SemVer No
? Footer. Information about Breaking Changes and reference issues that this commit closes: (press [enter] to skip)
 

ci: add commitizen to the project and add task commit shortcut in taskipy config

[WARNING] Unstaged files detected.
[INFO] Stashing unstaged files to /Users/bruno.nonogaki/.cache/pre-commit/patch1764946797-97283.
commitizen check.........................................................Passed
[INFO] Restored changes from /Users/bruno.nonogaki/.cache/pre-commit/patch1764946797-97283.

[commitlint dd5cfdf] ci: add commitizen to the project and add task commit shortcut in taskipy config
 2 files changed, 65 insertions(+), 6 deletions(-)

Commit successful!
```

## Adicionando o commitizen no CI

Agora vamos adicionar a verificação do `commitizen` no CI do fluxo do Github Actions. Para isso, vamos adicionar uma task no workflow `lint.yaml`. E para o `commitizen` poder analisar todos os commits dentro de um Pull Request, precisamos adicionar a opção `fetch-depth: 0` na action de checkout. Caso contrário, a action só traz o último commit.

```yaml title="./.github/workflows/lint.yaml" hl_lines="28-50"
name: Linting

on: pull_request

jobs:
  ruff:
    name: ruff
    runs-on: ubuntu-latest

    steps:
      - name: "Download code"    
        uses: actions/checkout@v4

      - name: "Install Python 3.13"
        uses: actions/setup-python@v5
        with:
          python-version: '3.13'    

      - name: "Install Poetry"
        run: pipx install poetry

      - name: "Install dependencies"
        run: poetry install

      - name: "Run linting"
        run: poetry run task lint

  commitizen:
    name: commitizen
    runs-on: ubuntu-latest

    steps:
      - name: "Download code"    
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: "Install Python 3.13"
        uses: actions/setup-python@v5
        with:
          python-version: '3.13'    

      - name: "Install Poetry"
        run: pipx install poetry

      - name: "Install dependencies"
        run: poetry install

      - name: "Commitizen"
        run: poetry run cz check --rev-range origin/main..HEAD
```

!!! note

    Agora o nosso CI vai validar as mensagens de commit. Se for o caso, adicione essa regra no `ruleset` nas configurações do repositório, para que ele não permita o Merge para a branch `main` no caso de falha.