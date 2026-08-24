#!/usr/bin/env python3
"""
Port and apply AyuGramDesktop fork features and quality gates onto the upstream sandbox.
"""

import os
import shutil
import subprocess
import sys

SANDBOX_ROOT = os.path.join(os.environ.get("TEMP", "."), "ayugram_upstream_sandbox")
FORK_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def run_git(args, cwd=SANDBOX_ROOT):
    res = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=False)
    return res.returncode, res.stdout.strip(), res.stderr.strip()

def copy_tree_overwrite(src_rel, dst_rel=None):
    if dst_rel is None:
        dst_rel = src_rel
    src = os.path.join(FORK_ROOT, src_rel)
    dst = os.path.join(SANDBOX_ROOT, dst_rel)
    if os.path.isdir(src):
        os.makedirs(dst, exist_ok=True)
        for item in os.listdir(src):
            s = os.path.join(src, item)
            d = os.path.join(dst, item)
            if os.path.isdir(s):
                shutil.copytree(s, d, dirs_exist_ok=True)
            else:
                shutil.copy2(s, d)
    elif os.path.isfile(src):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)

def main():
    print(f"Applying Fork Features to Sandbox: {SANDBOX_ROOT}")
    if not os.path.exists(SANDBOX_ROOT):
        print(f"Error: Sandbox does not exist at {SANDBOX_ROOT}")
        sys.exit(1)

    # 1. Copy full directories
    directories = [
        "scripts",
        "tests",
        ".github",
        ".devcontainer",
        ".vscode",
        ".claude",
        ".agents",
        "docs",
        "Telegram/SourceFiles/ayu",
    ]
    for d in directories:
        print(f"Syncing {d}...")
        copy_tree_overwrite(d)

    # 2. Copy root documents & metadata
    root_files = [
        "PRODUCT.md",
        "REVIEW.md",
        "SECURITY_COMPLIANCE_MATRIX.md",
        "SUBMODULES.md",
        ".gitattributes",
        ".gitignore",
        ".devcontainer.json",
    ]
    for f in root_files:
        print(f"Syncing {f}...")
        copy_tree_overwrite(f)

    # 3. Copy individual updated files
    individual_files = [
        "Telegram/SourceFiles/storage/details/storage_file_utilities_kdf_test.cpp",
        "Telegram/SourceFiles/boxes/about_box.cpp",
        "Telegram/SourceFiles/boxes/boxes.style",
        "Telegram/SourceFiles/boxes/passcode_box.cpp",
        "Telegram/SourceFiles/settings.h",
        "Telegram/SourceFiles/settings.cpp",
        "Telegram/SourceFiles/settings/sections/settings_local_passcode.cpp",
        "Telegram/SourceFiles/storage/details/storage_file_utilities.h",
        "Telegram/SourceFiles/storage/details/storage_file_utilities.cpp",
        "Telegram/SourceFiles/storage/storage_domain.h",
        "Telegram/SourceFiles/storage/storage_domain.cpp",
        "Telegram/SourceFiles/window/window_lock_widgets.cpp",
        "Telegram/CMakeLists.txt",
        "Telegram/cmake/lib_tgcalls.cmake",
        "Telegram/build/prepare/prepare.py",
        "Telegram/build/docker/centos_env/Dockerfile",
        "Telegram/build/docker/centos_env/poetry.lock",
        "Telegram/build/docker/centos_env/pyproject.toml",
        "Telegram/build/docker/centos_env/requirements-build.txt",
        "Telegram/build/docker/centos_env/run.sh",
        "Telegram/build/qt_version.py",
    ]
    for f in individual_files:
        print(f"Syncing {f}...")
        copy_tree_overwrite(f)

    # 4. Apply hooks to application.cpp
    app_path = os.path.join(SANDBOX_ROOT, "Telegram/SourceFiles/core/application.cpp")
    with open(app_path, "r", encoding="utf-8") as f:
        app_content = f.read()

    if '#include "ayu/data/ayu_database.h"' not in app_content:
        app_content = app_content.replace(
            '#include "ayu/ayu_infra.h"',
            '#include "ayu/ayu_infra.h"\n#include "ayu/data/ayu_database.h"'
        )
    if "AyuDatabase::zeroizeKey();" not in app_content:
        app_content = app_content.replace(
            "void Application::lockByPasscode() {\n\t_passcodeLock = true;",
            "void Application::lockByPasscode() {\n\t_passcodeLock = true;\n\tAyuDatabase::zeroizeKey();"
        )
        if "AyuDatabase::zeroizeKey();" not in app_content:
            # fallback if pattern differed
            app_content = app_content.replace(
                "void Application::lockByPasscode() {",
                "void Application::lockByPasscode() {\n\tAyuDatabase::zeroizeKey();"
            )
    with open(app_path, "w", encoding="utf-8") as f:
        f.write(app_content)
    print("Patched application.cpp")

    # 5. Apply hooks to data_session.cpp
    ds_path = os.path.join(SANDBOX_ROOT, "Telegram/SourceFiles/data/data_session.cpp")
    with open(ds_path, "r", encoding="utf-8") as f:
        ds_content = f.read()

    passcode_check = "!(AyuSecurity::isPasscodeProtected() && Core::App().passcodeLocked())"
    if passcode_check not in ds_content:
        target_str = "if (settings.saveMessagesHistory() && !existing->isLocal() && !existing->author()->isSelf() && !edit.isEditHide) {"
        repl_str = "if (settings.saveMessagesHistory() && !existing->isLocal() && !existing->author()->isSelf() && !edit.isEditHide\n\t\t&& " + passcode_check + ") {"
        ds_content = ds_content.replace(target_str, repl_str)
    with open(ds_path, "w", encoding="utf-8") as f:
        f.write(ds_content)
    print("Patched data_session.cpp")

    print("\n[SUCCESS] All fork features and hooks ported to sandbox successfully!")

if __name__ == "__main__":
    main()
