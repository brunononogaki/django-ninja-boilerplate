#!/usr/bin/env python3
"""
rename.py — Personaliza o Django Ninja Boilerplate para um novo projeto.

Uso interativo:
    python rename.py

Uso direto (dry-run):
    python rename.py --app petshop --backend api.petshop.com.br --frontend app.petshop.com.br

Aplicar mudanças:
    python rename.py --app petshop --backend api.petshop.com.br --frontend app.petshop.com.br --apply
"""

import argparse
import re
import shutil
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

# Valores atuais do boilerplate — o que será substituído
OLD_APP = "myapi"
OLD_CONTAINER_PREFIX = "boilerplate"
OLD_PROJECT_NAME = "django-ninja"
OLD_REPO_NAME = "django-ninja-boilerplate"
OLD_BACKEND_DOMAIN = "myapi.brunononogaki.com"
OLD_FRONTEND_DOMAIN = "react.brunononogaki.com"
OLD_ROOT_DOMAIN = "brunononogaki.com"


def get_root_domain(domain: str) -> str:
    """api.myapp.com.br → myapp.com.br | myapp.com → myapp.com"""
    parts = domain.split(".")
    return ".".join(parts[1:]) if len(parts) > 2 else domain


def build_replacements(app_name: str, backend_domain: str, frontend_domain: str) -> list[tuple[str, str]]:
    new_root = get_root_domain(backend_domain)
    return [
        # Domínios completos primeiro (mais específicos → menos específicos)
        (f"https://{OLD_BACKEND_DOMAIN}", f"https://{backend_domain}"),
        (f"https://{OLD_FRONTEND_DOMAIN}", f"https://{frontend_domain}"),
        (OLD_BACKEND_DOMAIN, backend_domain),
        (OLD_FRONTEND_DOMAIN, frontend_domain),
        (f".{OLD_ROOT_DOMAIN}", f".{new_root}"),
        (OLD_ROOT_DOMAIN, new_root),
        # Nomes de projeto / repo
        (OLD_REPO_NAME, app_name),
        # Container prefix (boilerplate_ → app_)
        (f"{OLD_CONTAINER_PREFIX}_", f"{app_name}_"),
        # Docker project name — padrão específico para não substituir a lib django-ninja
        (f"--project-name {OLD_PROJECT_NAME}", f"--project-name {app_name}"),
        # Módulo Python (myapi → app_name) — por último para não colidir com domínios
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
    for i, (old_line, new_line) in enumerate(
        zip(content.splitlines(), new_content.splitlines()), 1
    ):
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
        return f"  AVISO: pasta '{app_name}/' já existe, pulando rename."
    msg = f"  {OLD_APP}/ → {app_name}/"
    if apply:
        shutil.move(str(old_path), str(new_path))
    return msg


def ask(prompt: str) -> str:
    while True:
        value = input(f"  {prompt}: ").strip()
        if value:
            return value
        print("  Campo obrigatório.")


def validate_app_name(name: str) -> str | None:
    if not re.match(r"^[a-z][a-z0-9_]*$", name):
        return "Deve começar com letra minúscula e conter apenas [a-z, 0-9, _]."
    if name in {"myapi", "boilerplate", "django", "admin", "app"}:
        return f"'{name}' é reservado ou igual ao nome atual."
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Renomeia o Django Ninja Boilerplate para um novo projeto."
    )
    parser.add_argument("--app", help="Nome do app Python (ex: petshop)")
    parser.add_argument("--backend", help="Domínio do backend (ex: api.petshop.com.br)")
    parser.add_argument("--frontend", help="Domínio do frontend (ex: app.petshop.com.br)")
    parser.add_argument("--apply", action="store_true", help="Aplica as mudanças (padrão: dry-run)")
    args = parser.parse_args()

    print("\n  Django Ninja Boilerplate — Renomeador de Projeto")
    print("  " + "─" * 50)

    # Coleta interativa se args faltarem
    app_name = args.app
    if not app_name:
        app_name = ask("Nome do app (ex: petshop)")
    err = validate_app_name(app_name)
    if err:
        print(f"\n  Erro no nome do app: {err}")
        sys.exit(1)

    backend_domain = args.backend or ask("Domínio do backend (ex: api.petshop.com.br)")
    frontend_domain = args.frontend or ask("Domínio do frontend (ex: app.petshop.com.br)")

    replacements = build_replacements(app_name, backend_domain, frontend_domain)
    apply = args.apply

    mode = "APLICANDO MUDANÇAS" if apply else "DRY-RUN — nada será alterado (use --apply para aplicar)"
    print(f"\n  Modo: {mode}")
    print(f"  App:      {OLD_APP} → {app_name}")
    print(f"  Backend:  {OLD_BACKEND_DOMAIN} → {backend_domain}")
    print(f"  Frontend: {OLD_FRONTEND_DOMAIN} → {frontend_domain}")
    print(f"  Domínio:  .{OLD_ROOT_DOMAIN} → .{get_root_domain(backend_domain)}")
    print("  " + "─" * 50 + "\n")

    # 1. Substituições em arquivos (antes de renomear pasta)
    total_files = 0
    for path in iter_text_files(ROOT):
        diffs = replace_in_file(path, replacements, apply)
        if diffs:
            total_files += 1
            print(f"[arquivo] {path.relative_to(ROOT)}")
            for d in diffs[:8]:
                print(d)
            if len(diffs) > 8:
                print(f"  ... +{len(diffs) - 8} linha(s)")
            print()

    # 2. Rename da pasta myapi/ (por último)
    print("[pasta]")
    folder_msg = rename_app_folder(app_name, apply)
    if folder_msg:
        print(folder_msg)
    else:
        print(f"  Pasta '{OLD_APP}/' não encontrada, nada a renomear.")

    # Resumo
    print("\n  " + "─" * 50)
    if apply:
        print(f"  Concluído. {total_files} arquivo(s) modificado(s).")
        print(f"  Pasta: {OLD_APP}/ → {app_name}/")
        print("\n  Próximos passos:")
        print("  1. Copie .env.production.example → .env.production e preencha os secrets")
        print("  2. git add . && git commit -m 'chore: rename project to {app_name}'")
    else:
        print(f"  {total_files} arquivo(s) seriam modificados.")
        print(f"  Rode com --apply para aplicar as mudanças.")
    print()


if __name__ == "__main__":
    main()
