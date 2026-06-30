from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from enum import Enum
from importlib.metadata import Distribution, PackageNotFoundError, distribution
from pathlib import Path
from typing import Literal

UvUpgradeStrategy = Literal["add", "lock"]


class Installer(str, Enum):
    PIP = "pip"
    UV_PIP = "uv-pip"
    UV = "uv-project"
    UV_TOOL = "uv-tool"
    PIPX = "pipx"
    BREW = "brew"
    CONDA = "conda"
    MAMBA = "mamba"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class InstallerInfo:
    installer: Installer
    upgrade_cmd: str | None


def _is_pipx_environment() -> bool:
    """Check whether the current environment is inside a pipx-managed venv."""

    return "pipx/venvs" in sys.prefix or "pipx\\venvs" in sys.prefix


def _is_uv_tool_environment() -> bool:
    """Check whether the current environment is inside a uv tool-managed venv."""

    return "/uv/tools/" in sys.prefix or "\\uv\\tools\\" in sys.prefix


def _detect_conda_variant() -> Installer:
    """Return MAMBA if the Mamba executable is configured, otherwise CONDA."""

    return Installer.MAMBA if os.environ.get("MAMBA_EXE") else Installer.CONDA


def _detect_conda_environment() -> Installer | None:
    """Detect whether the current environment is a Conda (or Mamba) environment.

    Checks in two ways:
    - CONDA_PREFIX env var being set (i.e. a conda env is activated)
    - sys.prefix path containing a known conda distribution directory name

    Returns the installer, or None if not a conda environment.
    """

    conda_prefix = os.environ.get("CONDA_PREFIX", "")
    if conda_prefix and os.path.normcase(sys.prefix).startswith(
        os.path.normcase(conda_prefix)
    ):
        return _detect_conda_variant()

    prefix_lower = sys.prefix.lower()
    parts = prefix_lower.replace("\\", "/").split("/")
    conda_prefixes = ("conda", "miniconda", "miniforge", "mambaforge")

    if any(part.startswith(conda_prefixes) for part in parts):
        return _detect_conda_variant()

    return None


def _is_brew_environment() -> bool:
    """Check whether the Python executable lives under a Homebrew prefix."""
    exe = sys.executable.lower()
    return any(
        p in exe for p in ("/opt/homebrew/", "/usr/local/cellar/", "/home/linuxbrew/")
    )


def _get_installer_metadata(dist: Distribution) -> str | None:
    """Read the INSTALLER metadata file from a distribution, if present."""

    if (value := dist.read_text("INSTALLER")) is None:
        return None

    value = value.strip().lower()

    return value if value else None


def _has_uv_lock(max_depth: int = 3) -> bool:
    """Check whether a uv.lock file exists in a parent directory of sys.prefix."""

    parent = Path(sys.prefix)

    for _ in range(max_depth):
        parent = parent.parent

        if (parent / "uv.lock").exists():
            return True

    return False


def _get_upgrade_cmd(
    installer: Installer,
    package_name: str,
    uv_upgrade_strategy: UvUpgradeStrategy = "add",
) -> str | None:
    """Return the shell command to upgrade a package for the given installer."""

    if installer == Installer.UV:
        if uv_upgrade_strategy == "lock":
            return f"uv lock --upgrade-package {package_name}"

        return f"uv add {package_name} --upgrade-package {package_name}"

    commands: dict[Installer, str] = {
        Installer.PIP: f"pip install -U {package_name}",
        Installer.UV_PIP: f"uv pip install --upgrade {package_name}",
        Installer.UV_TOOL: f"uv tool upgrade {package_name}",
        Installer.PIPX: f"pipx upgrade {package_name}",
        Installer.BREW: f"brew upgrade {package_name}",
        Installer.CONDA: f"conda update {package_name}",
        Installer.MAMBA: f"mamba update {package_name}",
    }

    return commands.get(installer)


def detect_installer(
    package_name: str,
    uv_upgrade_strategy: UvUpgradeStrategy = "add",
) -> InstallerInfo | None:
    """Detect which installer was used to install the given package.

    Returns None if the package is not installed.
    """

    def _result(installer: Installer) -> InstallerInfo:
        return InstallerInfo(
            installer,
            _get_upgrade_cmd(installer, package_name, uv_upgrade_strategy),
        )

    try:
        dist = distribution(package_name)
    except PackageNotFoundError:
        return None

    # Step 2: filesystem / environment checks
    if _is_pipx_environment():
        return _result(Installer.PIPX)

    if _is_uv_tool_environment():
        return _result(Installer.UV_TOOL)

    if conda_result := _detect_conda_environment():
        return _result(conda_result)

    if _is_brew_environment():
        return _result(Installer.BREW)

    # Step 3: INSTALLER metadata
    metadata_value = _get_installer_metadata(dist)

    if metadata_value == "uv":
        if _has_uv_lock():
            return _result(Installer.UV)
        return _result(Installer.UV_PIP)

    if metadata_value == "pip":
        return _result(Installer.PIP)

    # Step 4: default
    return InstallerInfo(Installer.UNKNOWN, None)
