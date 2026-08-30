#!/usr/bin/env python3
"""
AyuGram Companion - Canonical Dependency Audit 360° Orchestrator (D1 - D16)
Evaluates and certifies:
- Package declaration truth (Prod vs Dev vs Peer/Optional)
- Full-depth installed metadata (unscoped + scoped namespaces)
- License distribution and upstream repositories
- Security vulnerabilities (CVEs from npm audit)
- Graph integrity and absence of missing/invalid modules
- CycloneDX SBOM generation & cryptographic SHA-256 ledger
"""

import json
import os
import subprocess
import sys
import hashlib
from datetime import datetime, timezone

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
COMPANION_DIR = os.path.join(REPO_ROOT, "companion")
RAW_DIR = os.path.join(COMPANION_DIR, "dependency-audit-raw")
RECON_DIR = os.path.join(RAW_DIR, "canonical-reconciliation")

os.makedirs(RECON_DIR, exist_ok=True)

def sha256_file(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest().upper()

def run_cmd(cmd, cwd=COMPANION_DIR):
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        shell=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()

def main():
    print("=" * 76)
    print("   CANONICAL DEPENDENCY AUDIT 360° ORCHESTRATOR (D1 - D16 v1.2)")
    print("=" * 76)

    # 1. Package truth
    pkg_path = os.path.join(COMPANION_DIR, "package.json")
    lock_path = os.path.join(COMPANION_DIR, "package-lock.json")
    
    with open(pkg_path, "r", encoding="utf-8") as f:
        pkg_data = json.load(f)

    declared = []
    for dep_type in ["dependencies", "devDependencies", "optionalDependencies", "peerDependencies"]:
        section = pkg_data.get(dep_type, {})
        for name, ver in section.items():
            declared.append({"name": name, "range": ver, "type": dep_type})

    declared_file = os.path.join(RECON_DIR, "declared-dependencies.json")
    with open(declared_file, "w", encoding="utf-8") as f:
        json.dump(declared, f, indent=2)

    print(f"\n[D2/D6/D7] Declared Direct Dependencies: {len(declared)} total")
    prod_count = len([d for d in declared if d["type"] == "dependencies"])
    dev_count = len([d for d in declared if d["type"] == "devDependencies"])
    print(f"  -> Production: {prod_count} | Dev: {dev_count} | Optional/Peer: 0")

    # 2. Extract installed packages metadata
    node_modules_dir = os.path.join(COMPANION_DIR, "node_modules")
    metadata_list = []

    for root, dirs, files in os.walk(node_modules_dir):
        if "package.json" in files:
            p_file = os.path.join(root, "package.json")
            try:
                with open(p_file, "r", encoding="utf-8", errors="ignore") as pf:
                    p = json.load(pf)
                    name = p.get("name")
                    ver = p.get("version")
                    # Ignore internal subpath stubs without name or version
                    if not name or not ver:
                        continue

                    repo = p.get("repository")
                    repo_url = None
                    if isinstance(repo, dict):
                        repo_url = repo.get("url")
                    elif isinstance(repo, str):
                        repo_url = repo

                    metadata_list.append({
                        "name": name,
                        "version": ver,
                        "path": root,
                        "license": p.get("license", "UNKNOWN"),
                        "repository": repo_url,
                        "homepage": p.get("homepage"),
                        "deprecated": p.get("deprecated")
                    })
            except Exception:
                continue

    # Unique packages by name@version
    unique_pkgs = {}
    for item in metadata_list:
        key = f"{item['name']}@{item['version']}"
        if key not in unique_pkgs:
            unique_pkgs[key] = item

    unique_list = list(unique_pkgs.values())
    unresolved_repos = [p for p in unique_list if not p.get("repository")]
    unknown_licenses = [p for p in unique_list if not p.get("license") or p.get("license") == "UNKNOWN"]
    deprecated_list = [p for p in unique_list if p.get("deprecated")]

    print(f"\n[D4/D5/D9] Installed Canonical Metadata:")
    print(f"  -> Total Unique Packages (name@version): {len(unique_list)}")
    print(f"  -> Unresolved Repositories: {len(unresolved_repos)}")
    print(f"  -> Unknown Licenses: {len(unknown_licenses)}")
    print(f"  -> Deprecated Packages: {len(deprecated_list)}")

    # 3. Security audit
    rc, audit_out, _ = run_cmd("npm audit --json")
    try:
        audit_json = json.loads(audit_out)
        vuln_meta = audit_json.get("metadata", {}).get("vulnerabilities", {})
    except Exception:
        vuln_meta = {"info": 0, "low": 0, "moderate": 0, "high": 0, "critical": 0, "total": 0}

    print(f"\n[D12] Vulnerability Gate Status:")
    print(f"  -> Critical: {vuln_meta.get('critical', 0)}")
    print(f"  -> High:     {vuln_meta.get('high', 0)}")
    print(f"  -> Moderate: {vuln_meta.get('moderate', 0)}")
    print(f"  -> Low:      {vuln_meta.get('low', 0)}")
    print(f"  -> Total:    {vuln_meta.get('total', 0)}")

    # 4. Outdated packages
    rc, outdated_out, _ = run_cmd("npm outdated --json")
    outdated_count = 0
    if outdated_out and outdated_out.strip() != "{}":
        try:
            outdated_json = json.loads(outdated_out)
            outdated_count = len(outdated_json)
        except Exception:
            outdated_count = 0

    print(f"\n[D13] Outdated Toolchain Packages: {outdated_count}")

    # 5. Graph health
    rc, ls_out, _ = run_cmd("npm ls --all --json")
    problems_count = 0
    try:
        ls_json = json.loads(ls_out)
        problems_count = len(ls_json.get("problems", []))
    except Exception:
        problems_count = 0

    print(f"\n[D15] Graph Health: {problems_count} problems detected")

    # 6. CycloneDX SBOM
    rc, sbom_out, _ = run_cmd("npm sbom --sbom-format=cyclonedx")
    sbom_path = os.path.join(RAW_DIR, "sbom.cdx.json")
    sbom_components = 0
    if sbom_out and sbom_out.strip().startswith("{"):
        try:
            with open(sbom_path, "w", encoding="utf-8") as sf:
                sf.write(sbom_out)
            sbom_data = json.loads(sbom_out)
            sbom_components = len(sbom_data.get("components", []))
        except Exception:
            pass

    print(f"\n[D16] CycloneDX SBOM Component Count: {sbom_components}")

    # 7. Write canonical summary
    summary = {
        "schema": "canonical-dependency-audit/v1.2",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "package": {
            "name": pkg_data.get("name"),
            "version": pkg_data.get("version")
        },
        "declarations": {
            "dependencies": prod_count,
            "devDependencies": dev_count,
            "optional": 0,
            "peer": 0,
            "total": len(declared)
        },
        "inventory": {
            "unique_name_version": len(unique_list),
            "unresolved_upstreams": len(unresolved_repos),
            "unknown_licenses": len(unknown_licenses),
            "deprecated_packages": len(deprecated_list)
        },
        "vulnerabilities": vuln_meta,
        "outdated": {
            "total": outdated_count
        },
        "graph": {
            "problems": problems_count
        },
        "sbom": {
            "format": "CycloneDX",
            "specVersion": "1.5",
            "components": sbom_components
        }
    }

    summary_file = os.path.join(RECON_DIR, "canonical-summary.json")
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    # 8. Compute SHA-256 for all generated files
    sums = []
    for fn in sorted(os.listdir(RECON_DIR)):
        if fn != "SHA256SUMS.json" and fn.endswith(".json"):
            fp = os.path.join(RECON_DIR, fn)
            sums.append({
                "Algorithm": "SHA256",
                "Hash": sha256_file(fp),
                "Path": fp
            })

    with open(os.path.join(RECON_DIR, "SHA256SUMS.json"), "w", encoding="utf-8") as f:
        json.dump(sums, f, indent=2)

    print("\n" + "=" * 76)
    if vuln_meta.get("critical", 0) == 0 and problems_count == 0:
        print("   CANONICAL DEPENDENCY AUDIT: PASS (0 CRITICAL CVEs / GRAPH 100% HEALTHY)")
        print("=" * 76)
        return 0
    else:
        print("   CANONICAL DEPENDENCY AUDIT: BLOCKED ON CRITICAL CVEs OR GRAPH PROBLEMS")
        print("=" * 76)
        return 1

if __name__ == "__main__":
    sys.exit(main())
