#!/usr/bin/env python3
import os
import shutil
import subprocess


def get_submodule_paths(root_dir):
    paths = [root_dir]
    gitmodules = os.path.join(root_dir, ".gitmodules")
    git_bin = shutil.which("git") or "git"
    if os.path.exists(gitmodules):
        res = subprocess.run(
            [git_bin, "-C", root_dir, "config", "--file", ".gitmodules", "--get-regexp", "path"],
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode == 0:
            for line in res.stdout.strip().splitlines():
                parts = line.split(None, 1)
                if len(parts) == 2:
                    sub_path = os.path.join(root_dir, parts[1])
                    if os.path.isdir(sub_path):
                        paths.extend(get_submodule_paths(sub_path))
    return list(dict.fromkeys(paths))


def resolve_repo_symlinks(repo_dir):
    git_bin = shutil.which("git") or "git"
    try:
        res = subprocess.run(
            [git_bin, "-C", repo_dir, "ls-files", "-s"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return 0

    if res.returncode != 0:
        return 0

    count = 0
    for line in res.stdout.strip().splitlines():
        parts = line.split()
        if len(parts) >= 4 and parts[0] == "120000":
            sha = parts[1]
            rel_path = " ".join(parts[3:])
            full_path = os.path.join(repo_dir, rel_path)

            try:
                cat_res = subprocess.run(
                    [git_bin, "-C", repo_dir, "cat-file", "-p", sha],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if cat_res.returncode != 0:
                    continue
                target = cat_res.stdout.strip()
            except OSError:
                continue

            if os.path.islink(full_path):
                if os.readlink(full_path) != target:
                    os.unlink(full_path)
                    os.symlink(target, full_path)
                    count += 1
            else:
                if os.path.exists(full_path):
                    os.remove(full_path)
                os.symlink(target, full_path)
                count += 1
                print(f"Fixed symlink: {rel_path} -> {target}")

    return count

def main():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    repos = get_submodule_paths(root)
    total_fixed = 0
    for r in repos:
        total_fixed += resolve_repo_symlinks(r)
    print(f"Total symlinks fixed: {total_fixed}")

if __name__ == "__main__":
    main()
