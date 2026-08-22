#!/usr/bin/env python3
"""
Upstream Conflict Matrix Analyzer for AyuGramDesktop (Pillar 4 / UPSTREAM-03).
Maps exact file intersections and collision risks between Fork patches (51 commits)
and Upstream updates (2,171 commits) since common merge-base.
"""

import json
import os
import shutil
import subprocess
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def run_cmd(args):
    git_bin = shutil.which("git") or "git"
    result = subprocess.run(
        [git_bin, *args],
        capture_output=True,
        text=True,
        shell=False,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def analyze_conflicts():
    print("=" * 80)
    print("      AYUGRAM DESKTOP — UPSTREAM CONFLICT MATRIX ANALYZER")
    print("=" * 80)

    # 1. Resolve merge base
    code, merge_base, _ = run_cmd(["merge-base", "HEAD", "upstream/dev"])
    if code != 0 or not merge_base:
        print("[ERROR] Could not determine merge-base with upstream/dev.")
        sys.exit(1)
        
    print(f"Merge-base SHA: {merge_base}")

    # 2. Get Fork modified files
    code, fork_files_raw, _ = run_cmd(["diff", "--name-only", f"{merge_base}..HEAD"])
    fork_files = {f.strip() for f in fork_files_raw.splitlines() if f.strip()}
    print(f"Total Fork Modified Files: {len(fork_files)}")

    # 3. Get Upstream modified files
    code, upstream_files_raw, _ = run_cmd(["diff", "--name-only", f"{merge_base}..upstream/dev"])
    upstream_files = {f.strip() for f in upstream_files_raw.splitlines() if f.strip()}
    print(f"Total Upstream Modified Files: {len(upstream_files)}")

    # 4. Compute Intersections
    intersecting_files = sorted(fork_files.intersection(upstream_files))
    fork_only_files = sorted(fork_files - upstream_files)
    
    print(f"Intersecting (Potential Conflict) Files: {len(intersecting_files)}")
    print(f"Fork-Isolated Files (Zero Collision):   {len(fork_only_files)}")

    # 5. Risk Classification
    matrix = []
    for file in intersecting_files:
        risk = "LOW"
        domain = "General"
        
        if "Telegram/SourceFiles/history/" in file or "Telegram/SourceFiles/window/" in file or "Telegram/SourceFiles/core/" in file:
            risk = "HIGH"
            domain = "Telegram Core UI & Message Lifecycle"
        elif "Telegram/SourceFiles/data/" in file or "Telegram/SourceFiles/storage/" in file:
            risk = "HIGH"
            domain = "Data / Storage Engine"
        elif "CMake" in file or "CMakeLists.txt" in file or "build" in file:
            risk = "MEDIUM"
            domain = "Build System & CMake"
        elif ".devcontainer" in file or ".github" in file:
            risk = "LOW"
            domain = "CI / DevContainer Config"
        elif "ThirdParty" in file or "submodule" in file:
            risk = "MEDIUM"
            domain = "ThirdParty Submodules"
            
        matrix.append({
            "file": file,
            "domain": domain,
            "risk": risk
        })

    # 6. Output Table
    print("\n| Risk Level | Subsystem / Domain | File Path |")
    print("| :---: | :--- | :--- |")
    for item in matrix:
        print(f"| **{item['risk']}** | {item['domain']} | `{item['file']}` |")

    # 7. Summary
    high_count = sum(1 for item in matrix if item['risk'] == 'HIGH')
    med_count = sum(1 for item in matrix if item['risk'] == 'MEDIUM')
    low_count = sum(1 for item in matrix if item['risk'] == 'LOW')

    print("\n" + "=" * 80)
    print(f"Risk Breakdown: HIGH={high_count} | MEDIUM={med_count} | LOW={low_count}")
    print(f"Fork-Isolated Safe Files: {len(fork_only_files)}")
    print("=" * 80)

    # 8. Save structured manifest
    output_path = os.path.join("scripts", "upstream_conflict_matrix.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "merge_base": merge_base,
            "total_fork_files": len(fork_files),
            "total_upstream_files": len(upstream_files),
            "total_intersecting": len(intersecting_files),
            "risk_summary": {
                "HIGH": high_count,
                "MEDIUM": med_count,
                "LOW": low_count
            },
            "matrix": matrix,
            "fork_only_files": fork_only_files
        }, f, indent=2)
    print(f"\nManifest successfully saved to: {output_path}")

if __name__ == "__main__":
    analyze_conflicts()
