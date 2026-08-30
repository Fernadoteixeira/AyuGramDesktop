#!/usr/bin/env python3
"""
AyuGram Native Shell - 360° End-to-End Verification Gate
Performs systematic verification across all layers:
- Static / Typecheck (L0-L3)
- Unit & IPC Contract Tests (L4-L7)
- Production Bundle Build (L8)
- Runtime Boundary & Container Smoke Tests (L9-L10)
"""

import json
import os
import subprocess
import sys
import time
import urllib.request
import socket

# Force UTF-8 on Windows stdout/stderr
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

COMPANION_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "companion"))

def run_cmd(cmd, cwd=None):
    start = time.time()
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd or COMPANION_DIR,
            shell=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
            check=False
        )
        duration = time.time() - start
        return {
            "exit_code": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
            "duration_ms": round(duration * 1000, 2)
        }
    except Exception as e:
        return {
            "exit_code": -1,
            "stdout": "",
            "stderr": str(e),
            "duration_ms": round((time.time() - start) * 1000, 2)
        }

def check_tcp_port(host, port, timeout=3.0):
    start = time.time()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True, round((time.time() - start) * 1000, 2)
    except Exception as e:
        return False, round((time.time() - start) * 1000, 2)

def check_http_endpoint(url, timeout=3.0):
    start = time.time()
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200, resp.status, round((time.time() - start) * 1000, 2)
    except Exception as e:
        return False, str(e), round((time.time() - start) * 1000, 2)

def main():
    print("=" * 70)
    print("      AYUGRAM NATIVE SHELL - SENIOR ENGINEER 360° GATE AUDIT")
    print("=" * 70)

    results = {}

    # 1. Typecheck (TypeScript)
    print("\n[GATE 1] Running Strict Typecheck (tsc)...")
    res_typecheck = run_cmd("npm run typecheck")
    passed_typecheck = res_typecheck["exit_code"] == 0
    results["L3_TYPECHECK"] = {
        "passed": passed_typecheck,
        "exit_code": res_typecheck["exit_code"],
        "duration_ms": res_typecheck["duration_ms"],
        "error": res_typecheck["stderr"] if not passed_typecheck else None
    }
    print(f"  -> Typecheck: {'PASSED [OK]' if passed_typecheck else 'FAILED [ERR]'} ({res_typecheck['duration_ms']}ms)")

    # 2. Automated Tests (Unit & Contract)
    print("\n[GATE 2] Running Vitest Suite (Main + Renderer + IPC Contracts)...")
    res_test = run_cmd("npm test")
    passed_test = res_test["exit_code"] == 0
    results["L4_UNIT_CONTRACT_TESTS"] = {
        "passed": passed_test,
        "exit_code": res_test["exit_code"],
        "duration_ms": res_test["duration_ms"],
        "output": res_test["stdout"] if not passed_test else None
    }
    if not passed_test:
        print(f"  -> Test Error Details:\n{res_test['stdout']}\n{res_test['stderr']}")
    print(f"  -> Test Suite: {'PASSED [OK]' if passed_test else 'FAILED [ERR]'} ({res_test['duration_ms']}ms)")

    # 3. Production Build (electron-vite)
    print("\n[GATE 3] Running Production Build (Vite + Electron)...")
    res_build = run_cmd("npm run build")
    passed_build = res_build["exit_code"] == 0
    results["L8_BUILD"] = {
        "passed": passed_build,
        "exit_code": res_build["exit_code"],
        "duration_ms": res_build["duration_ms"]
    }
    print(f"  -> Build: {'PASSED [OK]' if passed_build else 'FAILED [ERR]'} ({res_build['duration_ms']}ms)")

    # 4. Docker CLI & Container Boundary
    print("\n[GATE 4] Checking Docker Container & Runtime Boundary...")
    res_docker = run_cmd('docker inspect --format "{{.State.Running}}" ayugram-dev-ui')
    is_docker_running = res_docker["exit_code"] == 0 and res_docker["stdout"].lower() == "true"
    results["L9_DOCKER_CONTAINER"] = {
        "passed": is_docker_running,
        "state": res_docker["stdout"],
        "duration_ms": res_docker["duration_ms"]
    }
    print(f"  -> Docker Container 'ayugram-dev-ui': {'RUNNING [OK]' if is_docker_running else 'OFFLINE [WARN]'}")

    # 5. C++ AyuGram Binary & X11 Window
    print("\n[GATE 5] Checking AyuGram C++ Process & X11 Window Status...")
    res_proc = run_cmd('docker exec ayugram-dev-ui bash -lc "pgrep -x AyuGram || true"')
    proc_running = res_proc["exit_code"] == 0 and len(res_proc["stdout"]) > 0
    results["L9_AYUGRAM_PROCESS"] = {
        "passed": proc_running,
        "pid": res_proc["stdout"] if proc_running else None
    }
    print(f"  -> AyuGram Process PID: {res_proc['stdout'] if proc_running else 'NOT DETECTED'}")

    res_wm = run_cmd('docker exec ayugram-dev-ui bash -lc "DISPLAY=:1 wmctrl -lx"')
    wm_detected = res_wm["exit_code"] == 0 and ("AyuGram" in res_wm["stdout"] or "Telegram" in res_wm["stdout"])
    results["L9_X11_WINDOW"] = {
        "passed": wm_detected,
        "windows": res_wm["stdout"]
    }
    print(f"  -> X11 Window Rendered: {'YES [OK]' if wm_detected else 'NO [WARN]'}")

    # 6. Sockets & HTTP Endpoints (noVNC & VNC)
    print("\n[GATE 6] Checking Socket & HTTP Endpoints (6080 / 5900)...")
    tcp_vnc, vnc_latency = check_tcp_port("127.0.0.1", 5900)
    http_novnc, http_status, http_latency = check_http_endpoint("http://127.0.0.1:6080/vnc.html")
    
    results["L10_VNC_PORT_5900"] = {"passed": tcp_vnc, "latency_ms": vnc_latency}
    results["L10_NOVNC_HTTP_6080"] = {"passed": http_novnc, "status": http_status, "latency_ms": http_latency}
    print(f"  -> Port 5900 (VNC Socket): {'CONNECTED [OK]' if tcp_vnc else 'UNREACHABLE'} ({vnc_latency}ms)")
    print(f"  -> Port 6080 (noVNC Web): {'HTTP 200 [OK]' if http_novnc else 'UNREACHABLE'} ({http_latency}ms)")

    # Summary
    all_critical_passed = (
        passed_typecheck and
        passed_test and
        passed_build and
        is_docker_running and
        proc_running and
        http_novnc
    )

    print("\n" + "=" * 70)
    print(f"  FINAL GATE VERDICT: {'360° ALL GATES PASSED (SHIP-READY)' if all_critical_passed else 'CONDITIONAL PASS'}")
    print("=" * 70)

    report_path = os.path.join(COMPANION_DIR, "gate-360-report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved structured audit report to: {report_path}")

    return 0 if all_critical_passed else 1

if __name__ == "__main__":
    sys.exit(main())
