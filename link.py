#!/usr/bin/env python3

import sys
import os
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent
APP_NAME = "telly-spelly"
HOME = Path.home()

SYMLINKS = {
    HOME / ".local/share/telly-spelly": REPO_DIR,
    HOME / ".local/share/icons/hicolor/256x256/apps/telly-spelly.png": REPO_DIR / "telly-spelly.png",
}

GENERATED = {
    HOME / ".local/bin/telly-spelly": """\
#!/bin/bash
cd {repo}
exec {repo}/.venv/bin/python {repo}/main.py "$@"
""",
    HOME / ".local/share/applications/org.kde.telly_spelly.desktop": """\
[Desktop Entry]
Name=Telly Spelly
Comment=Record and transcribe audio using Whisper
Version=1.0
Exec={bin}
Icon=telly-spelly
Type=Application
Categories=Qt;KDE;Audio;AudioVideo;
Terminal=false
X-KDE-StartupNotify=true
""",
}


def cmd_link():
    for target, source in SYMLINKS.items():
        if target.exists() or target.is_symlink():
            if target.resolve() == source.resolve():
                print(f"  already linked: {target}")
                continue
            target.unlink()
            print(f"  removed: {target}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.symlink_to(source)
        print(f"  linked: {target} -> {source}")

    for target, template in GENERATED.items():
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.name == APP_NAME:
            content = template.format(repo=REPO_DIR)
        else:
            content = template.format(bin=HOME / ".local/bin/telly-spelly")
        if target.exists() and target.read_text() == content:
            print(f"  up to date: {target}")
            continue
        target.write_text(content)
        if target.name == APP_NAME:
            target.chmod(0o755)
        print(f"  wrote: {target}")


def cmd_unlink():
    for target in SYMLINKS:
        if target.is_symlink() or target.exists():
            target.unlink()
            print(f"  removed: {target}")
        else:
            print(f"  not found: {target}")
    for target in GENERATED:
        if target.exists():
            target.unlink()
            print(f"  removed: {target}")
        else:
            print(f"  not found: {target}")


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("link", "unlink"):
        print(f"Usage: {sys.argv[0]} [link|unlink]")
        sys.exit(1)

    action = sys.argv[1]
    print(f"{action.capitalize()}ing {APP_NAME}...")
    if action == "link":
        cmd_link()
    else:
        cmd_unlink()
    print("Done.")


if __name__ == "__main__":
    main()
