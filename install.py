#!/usr/bin/env python3

import os
import shutil
from pathlib import Path
import sys
import subprocess

def check_system_whisper():
    """Check if whisper is installed system-wide"""
    try:
        result = subprocess.run(
            [sys.executable, '-c', 'import whisper; print(whisper.__version__)'],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print(f"Found system whisper: {result.stdout.strip()}")
            return True
    except Exception:
        pass
    return False

def check_system_torch():
    """Check if torch is installed system-wide"""
    try:
        result = subprocess.run(
            [sys.executable, '-c', 'import torch; print(torch.__version__)'],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print(f"Found system torch: {result.stdout.strip()}")
            return True
    except Exception:
        pass
    return False

def create_venv(venv_path):
    """Create a virtual environment with system site packages"""
    print(f"Creating virtual environment at {venv_path}...")
    try:
        subprocess.check_call([
            sys.executable, '-m', 'venv', '--system-site-packages', str(venv_path)
        ])
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to create virtual environment: {e}")
        return False

def install_venv_requirements(venv_path, requirements_file):
    """Install requirements into the virtual environment"""
    pip_path = venv_path / 'bin' / 'pip'
    print("Installing dependencies into virtual environment...")
    try:
        subprocess.check_call([
            str(pip_path), 'install', '-r', str(requirements_file)
        ])
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to install requirements: {e}")
        return False

def install_application():
    # Define paths
    home = Path.home()
    app_name = "telly-spelly"
    source_dir = Path.cwd()

    # Check for system whisper and torch
    print("\nChecking prerequisites...")
    if not check_system_whisper():
        print("\nERROR: OpenAI Whisper is not installed system-wide.")
        print("Please install it first:")
        print("  sudo pip install openai-whisper --break-system-packages")
        return False

    if not check_system_torch():
        print("\nERROR: PyTorch is not installed system-wide.")
        print("Please install it first:")
        print("  sudo pip install torch --break-system-packages")
        return False

    # Create application directories
    app_dir = home / ".local/share/telly-spelly"
    bin_dir = home / ".local/bin"
    desktop_dir = home / ".local/share/applications"
    icon_dir = home / ".local/share/icons/hicolor/256x256/apps"
    venv_path = app_dir / ".venv"

    # Create directories if they don't exist
    for directory in [app_dir, bin_dir, desktop_dir, icon_dir]:
        directory.mkdir(parents=True, exist_ok=True)

    # Copy application files
    python_files = [
        "main.py", "recorder.py", "transcriber.py", "settings.py",
        "progress_window.py", "processing_window.py", "settings_window.py",
        "loading_window.py", "shortcuts.py", "volume_meter.py",
        "clipboard_manager.py", "__init__.py"
    ]

    for file in python_files:
        src = source_dir / file
        if src.exists():
            shutil.copy2(src, app_dir)
        else:
            print(f"Warning: Could not find {file}")

    # Copy requirements.txt
    requirements_file = source_dir / 'requirements.txt'
    if requirements_file.exists():
        shutil.copy2(requirements_file, app_dir)

    # Create virtual environment with system site packages
    if not create_venv(venv_path):
        print("Failed to create virtual environment. Installation aborted.")
        return False

    # Install additional requirements into venv
    if not install_venv_requirements(venv_path, app_dir / 'requirements.txt'):
        print("Failed to install requirements. Installation aborted.")
        return False

    # Create launcher script using venv python
    venv_python = venv_path / 'bin' / 'python'
    launcher_path = bin_dir / app_name
    with open(launcher_path, 'w') as f:
        f.write(f'''#!/bin/bash
cd {app_dir}
exec {venv_python} {app_dir}/main.py "$@"
''')

    # Make launcher executable
    launcher_path.chmod(0o755)

    # Copy desktop file and update Exec path
    desktop_file = "org.kde.telly_spelly.desktop"
    src_desktop = source_dir / desktop_file
    if src_desktop.exists():
        shutil.copy2(src_desktop, desktop_dir)
        # Update Exec line to use absolute path
        desktop_path = desktop_dir / desktop_file
        with open(desktop_path, 'r') as f:
            desktop_content = f.read()
        desktop_content = desktop_content.replace('Exec=telly-spelly', f'Exec={launcher_path}')
        with open(desktop_path, 'w') as f:
            f.write(desktop_content)
    else:
        print(f"Warning: Could not find {desktop_file}")

    # Copy icon
    icon_file = "telly-spelly.png"
    src_icon = source_dir / icon_file
    if src_icon.exists():
        shutil.copy2(src_icon, icon_dir)
    else:
        print(f"Warning: Could not find {icon_file}")

    print("\n" + "="*50)
    print("Installation completed!")
    print("="*50)
    print(f"Application installed to: {app_dir}")
    print(f"Launcher created at: {launcher_path}")
    print("\nYou may need to log out and back in for the application")
    print("to appear in your menu.")
    return True

if __name__ == "__main__":
    try:
        success = install_application()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Installation failed: {e}")
        sys.exit(1)
