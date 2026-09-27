"""Exporta o contrato OpenAPI de um app FastAPI em YAML, sem subir o servidor.

Uso:
    python scripts/exportar_openapi.py --app main:app --dir . [--saida contrato.yaml]

Sem --saida, o YAML vai para o stdout.
"""

import argparse
import contextlib
import importlib
import sys
from pathlib import Path

import yaml


def carregar_app(alvo: str, pasta: str):
    modulo_nome, _, atributo = alvo.partition(":")
    if not modulo_nome or not atributo:
        raise SystemExit(f"--app deve estar no formato modulo:variavel (recebido: {alvo!r})")

    sys.path.insert(0, str(Path(pasta).resolve()))

    # Prints e logs emitidos durante o import não podem contaminar o contrato.
    with contextlib.redirect_stdout(sys.stderr):
        modulo = importlib.import_module(modulo_nome)
        app = getattr(modulo, atributo)
        if not hasattr(app, "openapi") and callable(app):
            app = app()  # factory, ex.: create_app

    if not hasattr(app, "openapi"):
        raise SystemExit(f"{alvo} não é um app FastAPI")
    return app


def main() -> None:
    # Parte da equipe usa Windows, onde o stdout não é UTF-8 por padrão.
    sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--app", required=True, help="modulo:variavel, ex.: main:app")
    parser.add_argument("--dir", default=".", help="pasta do serviço (entra no sys.path)")
    parser.add_argument("--saida", help="arquivo YAML de saída (padrão: stdout)")
    args = parser.parse_args()

    app = carregar_app(args.app, args.dir)
    with contextlib.redirect_stdout(sys.stderr):
        esquema = app.openapi()

    conteudo = yaml.dump(esquema, sort_keys=False, allow_unicode=True)

    if args.saida:
        Path(args.saida).parent.mkdir(parents=True, exist_ok=True)
        with open(args.saida, "w", encoding="utf-8", newline="\n") as f:
            f.write(conteudo)
    else:
        sys.stdout.write(conteudo)


if __name__ == "__main__":
    main()
