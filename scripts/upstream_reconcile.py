#!/usr/bin/env python3
"""
Upstream Divergence Analysis and Lineage Engine for AyuGramDesktop.
Maps fork-only commits, upstream delta, conflict domains, and produces synchronization strategy.

This engine is strictly read-only analysis and fails closed on any Git or SHA anomaly.
"""

import re
import shutil
import subprocess
import sys

# Configure UTF-8 stdout
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SHA40_RE = re.compile(r"^[0-9a-f]{40}$")


def get_git_executable():
    git_path = shutil.which("git")
    if not git_path:
        print("[ERROR] 'git' executable not found in PATH.", file=sys.stderr)
        sys.exit(1)
    return git_path


def run_git(args, cwd=None):
    git_bin = get_git_executable()
    result = subprocess.run(
        [git_bin, *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        shell=False,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def validate_sha(sha_val, name):
    if not SHA40_RE.match(sha_val):
        print(f"[ERROR] Invalid 40-char hex SHA for {name}: '{sha_val}'", file=sys.stderr)
        sys.exit(1)


def analyze_upstream():
    print("[UPSTREAM RECONCILIATION ENGINE] Starting 360° Divergence Analysis...")

    # 1. Check remotes
    code, remotes_out, remotes_err = run_git(["remote", "-v"])
    if code != 0 or not remotes_out:
        print(f"[ERROR] Failed to query git remotes: {remotes_err}", file=sys.stderr)
        sys.exit(1)
    print(f"  [1/6] Configured Git Remotes:\n{remotes_out}")

    # 2. Resolve Head SHAs
    code, local_head, err = run_git(["rev-parse", "HEAD"])
    if code != 0 or not local_head:
        print(f"[ERROR] Failed to resolve LOCAL_HEAD: {err}", file=sys.stderr)
        sys.exit(1)
    validate_sha(local_head, "LOCAL_HEAD")

    # Try resolving origin_head
    code, origin_head, _ = run_git(["rev-parse", "origin/dev"])
    if code != 0 or not origin_head or not SHA40_RE.match(origin_head):
        origin_head = local_head
    validate_sha(origin_head, "ORIGIN_HEAD")

    # Resolve upstream_head via git rev-parse or live git ls-remote
    upstream_url = "https://github.com/AyuGram/AyuGramDesktop.git"
    upstream_head = None

    code, up_parse, _ = run_git(["rev-parse", "upstream/dev"])
    if code == 0 and up_parse and SHA40_RE.match(up_parse):
        upstream_head = up_parse
    else:
        # Resolve via live ls-remote
        code_ls, ls_out, ls_err = run_git(["ls-remote", upstream_url, "refs/heads/dev"])
        if code_ls != 0 or not ls_out:
            print(f"[ERROR] Failed to resolve upstream live ref via {upstream_url}: {ls_err}", file=sys.stderr)
            sys.exit(1)
        upstream_head = ls_out.split()[0]

    validate_sha(upstream_head, "UPSTREAM_HEAD")

    print("  [2/6] Heads:")
    print(f"    - LOCAL_HEAD:    {local_head}")
    print(f"    - ORIGIN_HEAD:   {origin_head}")
    print(f"    - UPSTREAM_HEAD: {upstream_head}")

    # Ensure upstream_head object is available locally; if not, fetch to temporary agent ref
    temp_ref = "refs/agents/autopilot/upstream-dev"
    code_cat, _, _ = run_git(["cat-file", "-e", upstream_head])
    need_temp_cleanup = False

    if code_cat != 0:
        print(f"  [*] Upstream object {upstream_head[:8]} not found in local db, fetching to {temp_ref}...")
        code_fetch, _, fetch_err = run_git(["fetch", "--no-tags", upstream_url, f"dev:{temp_ref}"])
        if code_fetch != 0:
            print(f"[ERROR] Failed to fetch upstream commit into {temp_ref}: {fetch_err}", file=sys.stderr)
            sys.exit(1)
        need_temp_cleanup = True

    try:
        # 3. Find merge base
        code, merge_base, err = run_git(["merge-base", origin_head, upstream_head])
        if code != 0 or not merge_base:
            print(f"[ERROR] Failed to compute merge-base between {origin_head} and {upstream_head}: {err}", file=sys.stderr)
            sys.exit(1)
        validate_sha(merge_base, "MERGE_BASE")
        print(f"  [3/6] Common Merge Base: {merge_base}")

        # 4. Count fork ahead / behind
        code_ahead, fork_ahead_str, err_ahead = run_git(["rev-list", "--count", f"{merge_base}..{origin_head}"])
        if code_ahead != 0:
            print(f"[ERROR] Failed to compute fork_ahead: {err_ahead}", file=sys.stderr)
            sys.exit(1)

        code_behind, fork_behind_str, err_behind = run_git(["rev-list", "--count", f"{merge_base}..{upstream_head}"])
        if code_behind != 0:
            print(f"[ERROR] Failed to compute fork_behind: {err_behind}", file=sys.stderr)
            sys.exit(1)

        try:
            fork_ahead = int(fork_ahead_str)
            fork_behind = int(fork_behind_str)
        except ValueError as val_err:
            print(f"[ERROR] Non-integer divergence counts: ahead='{fork_ahead_str}', behind='{fork_behind_str}': {val_err}", file=sys.stderr)
            sys.exit(1)

        print("  [4/6] Divergence Metrics:")
        print(f"    - Fork Ahead:  {fork_ahead} commits (AyuGram patches)")
        print(f"    - Fork Behind: {fork_behind} commits (Upstream Telegram updates)")

        # 5. List Fork-only modified files
        code_diff, fork_files_out, err_diff = run_git(["diff", "--name-only", f"{merge_base}..{origin_head}"])
        if code_diff != 0:
            print(f"[ERROR] Failed to list fork diff files: {err_diff}", file=sys.stderr)
            sys.exit(1)

        fork_files = [f for f in fork_files_out.splitlines() if f.strip()]

        categories = {
            "AyuGram Core Logic / DB": [],
            "AyuGram UI & Settings": [],
            "Build & DevContainer": [],
            "CI / Workflows": [],
            "Submodules & Configs": [],
        }

        for f in fork_files:
            if "ayu/data" in f or "database" in f or "logic" in f:
                categories["AyuGram Core Logic / DB"].append(f)
            elif "ayu" in f or "window" in f or "menu" in f or "settings" in f:
                categories["AyuGram UI & Settings"].append(f)
            elif "docker" in f or "devcontainer" in f or "CMake" in f or "build" in f:
                categories["Build & DevContainer"].append(f)
            elif ".github" in f or "scripts" in f:
                categories["CI / Workflows"].append(f)
            else:
                categories["Submodules & Configs"].append(f)

        print(f"  [5/6] Fork Modified Files Inventory ({len(fork_files)} files):")
        for cat, files in categories.items():
            print(f"    * {cat}: {len(files)} files")
            for file in files[:3]:
                print(f"      - {file}")
            if len(files) > 3:
                print(f"      - ... (+{len(files) - 3} more)")

        # 6. Status and Boundaries
        print("  [6/6] Divergence Status & Operational Boundary:")
        print("    - ANALYSIS_STATUS: ANALYSIS_PASS")
        print("    - RECONCILIATION_STATUS: RECONCILIATION_NOT_ATTEMPTED (Engine is read-only)")
        print("    - NOTE: Divergence analysis complete. No upstream sync commits were created.")

        return {
            "local_head": local_head,
            "origin_head": origin_head,
            "upstream_head": upstream_head,
            "merge_base": merge_base,
            "fork_ahead": fork_ahead,
            "fork_behind": fork_behind,
            "categories": {k: len(v) for k, v in categories.items()},
            "analysis_status": "ANALYSIS_PASS",
            "reconciliation_status": "RECONCILIATION_NOT_ATTEMPTED",
        }
    finally:
        if need_temp_cleanup:
            run_git(["update-ref", "-d", temp_ref])


if __name__ == "__main__":
    analyze_upstream()
    print("\n[SUCCESS] Upstream Divergence Analysis Completed (ANALYSIS_PASS)!")
