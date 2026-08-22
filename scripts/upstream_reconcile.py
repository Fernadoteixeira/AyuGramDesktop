#!/usr/bin/env python3
"""
Upstream Divergence Analysis and Reconciliation Engine for AyuGramDesktop.
Maps fork-only commits, upstream delta, conflict domains, and produces synchronization strategy.
"""

import subprocess
import sys
import os
import json

# Configure UTF-8 stdout
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def run_cmd(cmd):
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        shell=True,
        encoding='utf-8',
        errors='replace',
        check=False
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()

def analyze_upstream():
    print("[UPSTREAM RECONCILIATION ENGINE] Starting 360° Divergence Analysis...")
    
    # 1. Check remotes
    code, remotes_out, _ = run_cmd("git remote -v")
    print(f"  [1/6] Configured Git Remotes:\n{remotes_out}")
    
    # 2. Resolve Head SHAs
    code, local_head, _ = run_cmd("git rev-parse HEAD")
    code, origin_head, _ = run_cmd("git rev-parse origin/dev")
    code, upstream_head, _ = run_cmd("git rev-parse upstream/dev")
    
    print("  [2/6] Heads:")
    print(f"    - LOCAL_HEAD:    {local_head}")
    print(f"    - ORIGIN_HEAD:   {origin_head}")
    print(f"    - UPSTREAM_HEAD: {upstream_head}")
    
    # 3. Find merge base
    code, merge_base, _ = run_cmd("git merge-base origin/dev upstream/dev")
    print(f"  [3/6] Common Merge Base: {merge_base}")
    
    # 4. Count fork ahead / behind
    code, fork_ahead, _ = run_cmd(f"git rev-list --count {merge_base}..origin/dev")
    code, fork_behind, _ = run_cmd(f"git rev-list --count {merge_base}..upstream/dev")
    
    print("  [4/6] Divergence Metrics:")
    print(f"    - Fork Ahead:  {fork_ahead} commits (AyuGram patches)")
    print(f"    - Fork Behind: {fork_behind} commits (Upstream Telegram updates)")
    
    # 5. List Fork-only modified files
    code, fork_files_out, _ = run_cmd(f"git diff --name-only {merge_base}..origin/dev")
    fork_files = [f for f in fork_files_out.splitlines() if f.strip()]
    
    categories = {
        "AyuGram Core Logic / DB": [],
        "AyuGram UI & Settings": [],
        "Build & DevContainer": [],
        "CI / Workflows": [],
        "Submodules & Configs": []
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
            
    # 6. Generate Reconciliation Strategy
    print("  [6/6] Recommended Reconciliation Strategy:")
    print("    1. Create disposable isolated sandbox branch: `sync/upstream-reconcile`")
    print("    2. Rebase/Cherry-pick AyuGram Core Logic onto fresh upstream HEAD")
    print("    3. Apply AyuGram UI adaptations aligning with latest Telegram UI architecture")
    print("    4. Re-execute test suite (T01-T22) on reconciled worktree")
    print("    5. Validate with zero regressions before PR generation")

    return {
        "local_head": local_head,
        "origin_head": origin_head,
        "upstream_head": upstream_head,
        "merge_base": merge_base,
        "fork_ahead": fork_ahead,
        "fork_behind": fork_behind,
        "categories": {k: len(v) for k, v in categories.items()}
    }

if __name__ == "__main__":
    result = analyze_upstream()
    print("\n[SUCCESS] Upstream Divergence Analysis & Reconciliation Matrix Completed!")
