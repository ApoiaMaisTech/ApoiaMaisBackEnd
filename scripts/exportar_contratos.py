"""Exporta o contrato OpenAPI de cada serviço listado em contratos.json.

Uso:
    python scripts/exportar_contratos.py [--saida pasta] [--docker] [--so nome ...]

Cada serviço roda em um subprocesso separado (os serviços podem ter pacotes com
o mesmo nome e dependências diferentes) e gera <saida>/<nome>.yaml.
Com --docker, a exportação roda dentro do container do serviço
(docker compose run --rm --no-deps -T), com este diretório scripts/ montado.

Campos de cada serviço em contratos.json:
    nome    nome do contrato (<nome>.yaml)
    dir     pasta do serviço, relativa à raiz do repo
    app     modulo:variavel do app FastAPI (ou da factory)
    docker  (opcional) nome do serviço no docker compose; padrão: nome
    python  (opcional) interpretador a usar; padrão: o atual
    env     (opcional) variáveis exigidas no import; só são usadas se ainda
            não estiverem definidas no ambiente (valores fictícios, nunca segredos)
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SCRIPTS = RAIZ / "scripts"
PASTA_SCRIPTS_CONTAINER = "/tmp/exportar-openapi"


def env_faltante(servico: dict) -> dict:
    return {k: v for k, v in servico.get("env", {}).items() if k not in os.environ}


def comando_local(servico: dict) -> tuple[list[str], dict]:
    cmd = [
        servico.get("python", sys.executable),
        str(SCRIPTS / "exportar_openapi.py"),
        "--app", servico["app"],
        "--dir", ".",
    ]
    env = {**os.environ, **env_faltante(servico), "PYTHONIOENCODING": "utf-8"}
    return cmd, env


def comando_docker(servico: dict) -> tuple[list[str], dict]:
    cmd = [
        "docker", "compose", "run", "--rm", "--no-deps", "-T",
        "-v", f"{SCRIPTS}:{PASTA_SCRIPTS_CONTAINER}:ro",
    ]
    for chave, valor in env_faltante(servico).items():
        cmd += ["-e", f"{chave}={valor}"]
    cmd += [
        servico.get("docker", servico["nome"]),
        "python", f"{PASTA_SCRIPTS_CONTAINER}/exportar_openapi.py",
        "--app", servico["app"],
        "--dir", ".",
    ]
    return cmd, {**os.environ}


def exportar(servico: dict, saida: Path, docker: bool) -> None:
    cmd, env = comando_docker(servico) if docker else comando_local(servico)
    cwd = RAIZ if docker else RAIZ / servico["dir"]

    resultado = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True)
    if resultado.returncode != 0:
        erro = resultado.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(erro[-3000:] or f"código de saída {resultado.returncode}")

    conteudo = resultado.stdout.decode("utf-8").replace("\r\n", "\n")
    if not conteudo.strip():
        raise RuntimeError("o exportador não gerou nenhum conteúdo")

    destino = saida / f"{servico['nome']}.yaml"
    with open(destino, "w", encoding="utf-8", newline="\n") as f:
        f.write(conteudo)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--saida", default="contratos", help="pasta de destino (padrão: contratos)")
    parser.add_argument("--docker", action="store_true", help="exporta dentro dos containers do docker compose")
    parser.add_argument("--so", nargs="+", metavar="NOME", help="exporta apenas estes serviços")
    args = parser.parse_args()

    servicos = json.loads((RAIZ / "contratos.json").read_text(encoding="utf-8"))["servicos"]
    if args.so:
        desconhecidos = set(args.so) - {s["nome"] for s in servicos}
        if desconhecidos:
            parser.error(f"serviço(s) desconhecido(s): {', '.join(sorted(desconhecidos))}")
        servicos = [s for s in servicos if s["nome"] in args.so]

    saida = Path(args.saida).resolve()
    saida.mkdir(parents=True, exist_ok=True)

    falhas = []
    for servico in servicos:
        try:
            exportar(servico, saida, args.docker)
            print(f"ok     {servico['nome']} -> {saida / (servico['nome'] + '.yaml')}")
        except Exception as e:
            falhas.append(servico["nome"])
            print(f"falhou {servico['nome']}:\n{e}\n", file=sys.stderr)

    if falhas:
        print(f"\nServiços com falha: {', '.join(falhas)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
