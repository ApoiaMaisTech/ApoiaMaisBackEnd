"""Prompt das ilustrações do jogo.

O prompt é montado SÓ no servidor, a partir de um template fixo e do tema da
fase (nome do mundo e da fase, conteúdo pedagógico). Nunca entra nada da
criança: nome, idade, diagnóstico, ids. Isso protege dados de paciente (LGPD),
impede injeção de prompt pelo jogo e permite reaproveitar a mesma imagem para
todas as crianças da fase (cache = menos custo).
"""
import hashlib
import re

from app.domain.entities.ai_image import StageTheme

# mudar o texto do template exige subir a versão: gera hashes novos e novas imagens
TEMPLATE_VERSION = "v1"
TEMPLATE = (
    "Ilustração infantil para um jogo educativo de alfabetização. "
    "Estilo livro ilustrado, cores suaves e alegres, traços simples, ambiente acolhedor. "
    "Sem texto, sem letras escritas, sem pessoas reais, sem violência, "
    "sem elementos assustadores e sem ambiente hospitalar. "
    "Tema: {theme}."
)
MAX_THEME_LENGTH = 160

_CONTROL = re.compile(r"[\x00-\x1f\x7f]")
_SPACES = re.compile(r"\s+")


def _clean(value: str) -> str:
    value = _CONTROL.sub(" ", value or "")
    return _SPACES.sub(" ", value).strip()


def build_theme(theme: StageTheme) -> str:
    parts = [p for p in (_clean(theme.world_name), _clean(theme.stage_name)) if p]
    return " - ".join(parts)[:MAX_THEME_LENGTH].strip()


def build_prompt(theme: StageTheme) -> str:
    return TEMPLATE.format(theme=build_theme(theme) or "aventura com as letras")


def prompt_hash(prompt: str) -> str:
    return hashlib.sha256(f"{TEMPLATE_VERSION}\n{prompt}".encode()).hexdigest()
