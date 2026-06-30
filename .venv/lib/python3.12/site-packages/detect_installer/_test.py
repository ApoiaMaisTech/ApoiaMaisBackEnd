from __future__ import annotations

import json
import sys

from detect_installer import detect_installer


def main() -> None:
    info = detect_installer("detect-installer")

    if info is None:
        print("Could not detect installer for detect-installer")
        sys.exit(1)

    json.dump(
        {
            "installer": info.installer.value,
            "upgrade_cmd": info.upgrade_cmd,
        },
        sys.stdout,
    )


if __name__ == "__main__":
    main()
