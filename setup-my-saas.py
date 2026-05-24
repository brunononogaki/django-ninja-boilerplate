#!/usr/bin/env python3
"""
setup-my-saas.py — Personaliza o Django Ninja Boilerplate para um novo projeto.

Uso:
    python3 setup-my-saas.py
"""

import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent

SKIP_DIRS = {
    ".git", "__pycache__", ".venv", "venv", "node_modules",
    ".mypy_cache", ".next", "docs", ".pytest_cache",
}
SKIP_FILES = {
    "poetry.lock",  # auto-gerado; django-ninja é dependência, não nome do projeto
}
BINARY_EXTENSIONS = {
    ".pyc", ".png", ".jpg", ".jpeg", ".svg", ".ico", ".gif",
    ".woff", ".woff2", ".ttf", ".eot", ".pdf", ".zip", ".tar", ".gz",
    ".db", ".sqlite3",
}
PREVIEW_LINES = 6

# Valores atuais do boilerplate — o que será substituído
OLD_APP = "myapi"
OLD_CONTAINER_PREFIX = "boilerplate"
OLD_PROJECT_NAME = "django-ninja"
OLD_REPO_NAME = "django-ninja-boilerplate"
OLD_BACKEND_DOMAIN = "myapi.brunononogaki.com"
OLD_FRONTEND_DOMAIN = "react.brunononogaki.com"
OLD_ROOT_DOMAIN = "brunononogaki.com"


# ─── helpers ──────────────────────────────────────────────────────────────────

def ask(prompt: str) -> str:
    while True:
        value = input(f"  {prompt}: ").strip()
        if value:
            return value
        print("  Campo obrigatório.")


def ask_optional(prompt: str) -> str:
    return input(f"  {prompt} (opcional, Enter para pular): ").strip()


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=ROOT, check=check, capture_output=True, text=True)


def ssh_run(host: str, user: str, port: str, key_file: Path, command: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["ssh", "-i", str(key_file), "-p", port, "-o", "StrictHostKeyChecking=no",
         f"{user}@{host}", command],
        capture_output=True, text=True,
    )


def get_root_domain(domain: str) -> str:
    parts = domain.split(".")
    return ".".join(parts[1:]) if len(parts) > 2 else domain


# ─── renomeação ───────────────────────────────────────────────────────────────

def build_replacements(app_name: str, backend_domain: str, frontend_domain: str) -> list[tuple[str, str]]:
    new_root = get_root_domain(backend_domain)
    return [
        (f"https://{OLD_BACKEND_DOMAIN}", f"https://{backend_domain}"),
        (f"https://{OLD_FRONTEND_DOMAIN}", f"https://{frontend_domain}"),
        (OLD_BACKEND_DOMAIN, backend_domain),
        (OLD_FRONTEND_DOMAIN, frontend_domain),
        (f".{OLD_ROOT_DOMAIN}", f".{new_root}"),
        (OLD_ROOT_DOMAIN, new_root),
        (OLD_REPO_NAME, app_name),
        (f"{OLD_CONTAINER_PREFIX}_", f"{app_name}_"),
        (f"--project-name {OLD_PROJECT_NAME}", f"--project-name {app_name}"),
        (OLD_APP, app_name),
    ]


def iter_text_files(root: Path):
    for path in sorted(root.rglob("*")):
        if path.is_dir():
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(root).parts):
            continue
        if path.suffix in BINARY_EXTENSIONS:
            continue
        if path.name in SKIP_FILES:
            continue
        if path.name == Path(__file__).name:
            continue
        yield path


def replace_in_file(path: Path, replacements: list[tuple[str, str]], apply: bool) -> list[str]:
    try:
        content = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, PermissionError, FileNotFoundError, OSError):
        return []

    new_content = content
    for old, new in replacements:
        new_content = new_content.replace(old, new)

    if new_content == content:
        return []

    diffs = []
    for i, (old_line, new_line) in enumerate(zip(content.splitlines(), new_content.splitlines()), 1):
        if old_line != new_line:
            diffs.append(f"  L{i}: {old_line.strip()!r}\n       → {new_line.strip()!r}")

    if apply:
        path.write_text(new_content, encoding="utf-8")

    return diffs


def rename_app_folder(app_name: str, apply: bool) -> str | None:
    old_path = ROOT / OLD_APP
    new_path = ROOT / app_name
    if not old_path.exists():
        return None
    if new_path.exists():
        return f"AVISO: pasta '{app_name}/' já existe, pulando rename."
    if apply:
        shutil.move(str(old_path), str(new_path))
    return f"{OLD_APP}/ → {app_name}/"


def validate_app_name(name: str) -> str | None:
    if not re.match(r"^[a-z][a-z0-9_]*$", name):
        return "Deve começar com letra minúscula e conter apenas [a-z, 0-9, _]."
    if name in {"myapi", "boilerplate", "django", "admin", "app"}:
        return f"'{name}' é reservado ou igual ao nome atual."
    return None


def remove_docs_deploy_step() -> None:
    deploy_yaml = ROOT / ".github" / "workflows" / "deploy.yaml"
    if not deploy_yaml.exists():
        return
    content = deploy_yaml.read_text(encoding="utf-8")
    docs_step = (
        "\n\n      - name: Build Documentation\n"
        "        uses: appleboy/ssh-action@v1.0.0\n"
        "        with:\n"
        "          host: ${{ secrets.DEPLOY_HOST }}\n"
        "          username: ${{ secrets.DEPLOY_USER }}\n"
        "          key: ${{ secrets.DEPLOY_SSH_KEY }}\n"
        "          port: ${{ secrets.DEPLOY_PORT || 22 }}\n"
        "          script: |\n"
        "            set -e\n"
        "            cd ${{ secrets.DEPLOY_PATH }}/docs\n"
        "            echo \"🚀 Subindo container do mkdocs...\"\n"
        "            docker compose down && docker compose up -d --build\n"
        "            echo \"✅ Deploy do mkdocs concluído!\""
    )
    new_content = content.replace(docs_step, "")
    if new_content != content:
        deploy_yaml.write_text(new_content, encoding="utf-8")
        print("  ✓ step 'Build Documentation' removido do deploy.yaml")


# ─── GitHub ───────────────────────────────────────────────────────────────────

def check_gh_auth() -> None:
    if not shutil.which("gh"):
        print("\n  GitHub CLI (gh) não encontrado. Instale em: https://cli.github.com")
        print("  O script continuará, mas a criação do repositório não estará disponível.\n")
        return
    auth = subprocess.run(["gh", "auth", "status"], capture_output=True, check=False)
    if auth.returncode != 0:
        print("\n  Você não está logado no GitHub CLI.")
        if input("  Fazer login agora? [s/N]: ").strip().lower() == "s":
            subprocess.run(["gh", "auth", "login"], check=False)
        else:
            print("  Continuando sem autenticação — criação do repositório não estará disponível.\n")


def setup_github(app_name: str) -> None:
    if not shutil.which("gh"):
        print("\n  gh não encontrado — pulando criação do repositório.")
        return

    visibilidade = input("  Repositório público ou privado? [privado/publico]: ").strip().lower()
    flag = "--public" if visibilidade == "publico" else "--private"

    print("\n  Recriando histórico git limpo...")
    shutil.rmtree(ROOT / ".git")
    run(["git", "init", "-b", "main"])
    run(["git", "add", "."])
    run(["git", "commit", "-m", f"chore: setup project {app_name} from django-ninja-boilerplate"])

    print(f"  Criando repositório '{app_name}' no GitHub ({flag[2:]})...")
    result = run(["gh", "repo", "create", app_name, flag, "--source=.", "--remote=origin"], check=False)

    if result.returncode != 0:
        print(f"\n  Erro ao criar repositório:\n  {result.stderr.strip()}")
        print("\n  O histórico git foi reiniciado. Crie o repo manualmente e rode:")
        print("    git remote add origin <url> && git push -u origin main")
        return

    url = run(["gh", "repo", "view", app_name, "--json", "url", "-q", ".url"], check=False)
    repo_url = url.stdout.strip() if url.returncode == 0 else ""
    if repo_url:
        print(f"  Repositório criado: {repo_url}")

    gh_user = run(["gh", "api", "user", "--jq", ".login"], check=False).stdout.strip()

    # Secrets e .env ANTES do push
    vps_info = setup_secrets(app_name, gh_user)
    if vps_info:
        setup_env_production(app_name, vps_info)

    # Push para main só depois que tudo estiver pronto
    print("\n  Fazendo push para main...")
    run(["git", "push", "-u", "origin", "main"])
    print("  ✓ main pushed")

    print("  Criando branch development...")
    run(["git", "checkout", "-b", "development"])
    run(["git", "push", "-u", "origin", "development"])
    print("  ✓ branch development criada e pushed")

    if repo_url:
        print(f"\n  Tudo pronto! {repo_url}")


def setup_secrets(app_name: str, gh_user: str = "") -> dict | None:
    repo_ref = f"{gh_user}/{app_name}" if gh_user else app_name
    print("\n  " + "─" * 50)
    if input("  Configurar secrets de deploy no GitHub Actions? [s/N]: ").strip().lower() != "s":
        return None

    print("\n  Informe os dados de acesso à VPS:")
    host = ask("IP ou hostname da VPS (DEPLOY_HOST)")
    user = input("  Usuário SSH (DEPLOY_USER) [root]: ").strip() or "root"
    path = ask("Caminho no servidor (DEPLOY_PATH, ex: /opt/petshop)")
    port = input("  Porta SSH (DEPLOY_PORT) [22]: ").strip() or "22"

    print("\n  Chave SSH privada (usada pelo GitHub Actions para acessar a VPS):")
    while True:
        key_path = input("  Caminho local da chave privada [~/.ssh/id_rsa]: ").strip() or "~/.ssh/id_rsa"
        key_file = Path(key_path).expanduser()
        if key_file.exists():
            break
        print(f"  Arquivo não encontrado: {key_file}")

    print()
    ok = True
    for name, value in {"DEPLOY_HOST": host, "DEPLOY_USER": user, "DEPLOY_PATH": path, "DEPLOY_PORT": port}.items():
        res = run(["gh", "secret", "set", name, "--repo", repo_ref, "--body", value], check=False)
        if res.returncode == 0:
            print(f"  ✓ {name}")
        else:
            print(f"  ✗ {name}: {res.stderr.strip()}")
            ok = False

    res = subprocess.run(
        ["gh", "secret", "set", "DEPLOY_SSH_KEY", "--repo", repo_ref],
        input=key_file.read_text(),
        cwd=ROOT, capture_output=True, text=True,
    )
    if res.returncode == 0:
        print("  ✓ DEPLOY_SSH_KEY")
    else:
        print(f"  ✗ DEPLOY_SSH_KEY: {res.stderr.strip()}")
        ok = False

    if not ok:
        print(f"\n  Algumas secrets falharam. Reconfigure com: gh secret set <NOME> --repo {repo_ref}")

    return {"host": host, "user": user, "path": path, "port": port, "key_file": key_file}


def setup_env_production(app_name: str, vps: dict) -> None:
    print("\n  " + "─" * 50)
    print("  Configurar .env.production:")

    pg_user = input("  POSTGRES_USER [postgres]: ").strip() or "postgres"
    pg_password = ask("POSTGRES_PASSWORD")
    pg_db = input(f"  POSTGRES_DB [{app_name}]: ").strip() or app_name
    secret_key = ask("SECRET_KEY (Django — use uma string longa e aleatória)")
    admin_user = input("  DJANGO_ADMIN_USER [admin]: ").strip() or "admin"
    admin_email = ask("DJANGO_ADMIN_EMAIL")
    admin_password = ask("DJANGO_ADMIN_PASSWORD")
    gmail_email = ask_optional("GMAIL_EMAIL")
    gmail_password = ask_optional("GMAIL_APP_PASSWORD")

    example = ROOT / ".env.production.example"
    content = example.read_text(encoding="utf-8") if example.exists() else ""

    replacements = [
        ("POSTGRES_USER=devuser", f"POSTGRES_USER={pg_user}"),
        ("POSTGRES_PASSWORD=devpassword", f"POSTGRES_PASSWORD={pg_password}"),
        ("POSTGRES_DB=postgres", f"POSTGRES_DB={pg_db}"),
        ("SECRET_KEY='mysecretkey-pro'", f"SECRET_KEY='{secret_key}'"),
        ("DJANGO_ADMIN_USER = 'admin'", f"DJANGO_ADMIN_USER = '{admin_user}'"),
        ("DJANGO_ADMIN_EMAIL = 'admin@admin.com'", f"DJANGO_ADMIN_EMAIL = '{admin_email}'"),
        ("DJANGO_ADMIN_PASSWORD = 'devpassword'", f"DJANGO_ADMIN_PASSWORD = '{admin_password}'"),
        ("GMAIL_EMAIL=email@gmail.com", f"GMAIL_EMAIL={gmail_email}" if gmail_email else "GMAIL_EMAIL="),
        ("GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx", f"GMAIL_APP_PASSWORD={gmail_password}" if gmail_password else "GMAIL_APP_PASSWORD="),
    ]
    for old, new in replacements:
        content = content.replace(old, new)

    env_file = ROOT / ".env.production"
    env_file.write_text(content, encoding="utf-8")
    print("  ✓ .env.production criado")

    # Cria a pasta na VPS se não existir
    print(f"\n  Criando pasta {vps['path']} na VPS...")
    res = ssh_run(vps["host"], vps["user"], vps["port"], vps["key_file"], f"mkdir -p {vps['path']}")
    if res.returncode == 0:
        print(f"  ✓ pasta {vps['path']} pronta")
    else:
        print(f"  ✗ erro ao criar pasta: {res.stderr.strip()}")
        return

    # Envia o .env.production para a VPS
    print("  Enviando .env.production para a VPS...")
    res = subprocess.run(
        ["scp", "-i", str(vps["key_file"]), "-P", vps["port"],
         "-o", "StrictHostKeyChecking=no",
         str(env_file), f"{vps['user']}@{vps['host']}:{vps['path']}/.env.production"],
        capture_output=True, text=True,
    )
    if res.returncode == 0:
        print("  ✓ .env.production enviado para a VPS")
    else:
        print(f"  ✗ erro no scp: {res.stderr.strip()}")


# ─── main ─────────────────────────────────────────────────────────────────────

def main():
    print("\n  Setup My SaaS — Django Ninja Boilerplate")
    print("  " + "─" * 50)

    check_gh_auth()

    while True:
        app_name = ask("Nome do app Python (ex: petshop)")
        err = validate_app_name(app_name)
        if err:
            print(f"  Erro: {err}")
        else:
            break

    backend_domain = ask("Domínio do backend  (ex: api.petshop.com.br)")
    frontend_domain = ask("Domínio do frontend (ex: app.petshop.com.br)")

    replacements = build_replacements(app_name, backend_domain, frontend_domain)

    print(f"\n  Resumo do que será alterado:")
    print(f"  App:      {OLD_APP} → {app_name}")
    print(f"  Backend:  {OLD_BACKEND_DOMAIN} → {backend_domain}")
    print(f"  Frontend: {OLD_FRONTEND_DOMAIN} → {frontend_domain}")
    print(f"  Domínio:  .{OLD_ROOT_DOMAIN} → .{get_root_domain(backend_domain)}")
    print("  " + "─" * 50 + "\n")

    total_files = 0
    for path in iter_text_files(ROOT):
        diffs = replace_in_file(path, replacements, apply=False)
        if diffs:
            total_files += 1
            print(f"  [arquivo] {path.relative_to(ROOT)}")
            for d in diffs[:PREVIEW_LINES]:
                print(d)
            if len(diffs) > PREVIEW_LINES:
                print(f"  ... +{len(diffs) - PREVIEW_LINES} linha(s)")
            print()

    folder_msg = rename_app_folder(app_name, apply=False)
    if folder_msg:
        print(f"  [pasta] {folder_msg}")

    print("\n  " + "─" * 50)
    print(f"  {total_files} arquivo(s) serão modificados.")
    if input("\n  Confirmar e aplicar as mudanças? [s/N]: ").strip().lower() != "s":
        print("\n  Cancelado. Nenhuma alteração foi feita.\n")
        sys.exit(0)

    print()
    for path in iter_text_files(ROOT):
        if replace_in_file(path, replacements, apply=True):
            print(f"  ✓ {path.relative_to(ROOT)}")

    folder_msg = rename_app_folder(app_name, apply=True)
    if folder_msg:
        print(f"  ✓ {folder_msg}")

    docs_path = ROOT / "docs"
    if docs_path.exists():
        shutil.rmtree(docs_path)
        print("  ✓ pasta docs/ removida")

    remove_docs_deploy_step()

    print("\n  " + "─" * 50)
    print(f"  Concluído! {total_files} arquivo(s) modificado(s).")

    if input("\n  Criar repositório no GitHub agora? [s/N]: ").strip().lower() == "s":
        setup_github(app_name)
    else:
        print(f"\n  Próximos passos:")
        print(f"  1. Copie .env.production.example → .env.production e preencha os secrets")
        print(f"  2. git add . && git commit -m 'chore: setup project {app_name}'")
    print()


if __name__ == "__main__":
    main()
