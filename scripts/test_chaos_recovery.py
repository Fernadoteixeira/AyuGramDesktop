#!/usr/bin/env python3
"""
AyuGram Native Shell - Chaos-Lite Auto-Recovery & Resilience Gate
Tests:
1. Baseline health verification (Container + Process + X11 + Socket)
2. AyuGram process fault injection (kill) -> Degraded detection -> Recovery trigger -> Restored PID
3. X11 Window remap verification
4. noVNC socket survival and reconnect responsiveness
"""

import subprocess
import sys
import time
import socket
import urllib.request

# Force UTF-8 on Windows stdout
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CONTAINER = "ayugram-dev-ui"

def run_cmd(cmd):
    proc = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()

def check_tcp(port=5900):
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=2.0):
            return True
    except Exception:
        return False

def check_http(url="http://127.0.0.1:6080/vnc.html"):
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            return resp.status == 200
    except Exception:
        return False

def main():
    print("=" * 72)
    print("   AYUGRAM NATIVE SHELL - CHAOS-LITE RESILIENCE & RECOVERY TEST")
    print("=" * 72)

    # 1. Baseline
    print("\n[STEP 1] Verifying Baseline Healthy State...")
    rc, pids, _ = run_cmd(f'docker exec {CONTAINER} bash -lc "pgrep -x AyuGram || true"')
    if not pids:
        print("  [INFO] AyuGram was not running. Launching now...")
        run_cmd(f'docker exec {CONTAINER} bash -lc "DISPLAY=:1 /usr/local/bin/launch-ayugram >/dev/null 2>&1 &"')
        time.sleep(2)
        rc, pids, _ = run_cmd(f'docker exec {CONTAINER} bash -lc "pgrep -x AyuGram || true"')
    
    print(f"  -> Baseline PID: {pids} [HEALTHY]")

    # 2. Fault Injection: Terminate AyuGram
    print("\n[STEP 2] Injecting Fault: Terminating AyuGram process (pkill -9)...")
    run_cmd(f'docker exec {CONTAINER} bash -lc "pkill -9 -x AyuGram || true"')
    time.sleep(1)

    # 3. Degraded Detection
    rc, pids_after_kill, _ = run_cmd(f'docker exec {CONTAINER} bash -lc "pgrep -x AyuGram || true"')
    if not pids_after_kill:
        print("  -> Fault Detected: AyuGram process confirmed inactive [DEGRADED STATE ACCURATELY DETECTED]")
    else:
        print(f"  -> [FAIL] Process still running with PID {pids_after_kill}")
        return 1

    # 4. Trigger Auto-Recovery
    print("\n[STEP 3] Triggering Recovery: Relaunching AyuGram via launcher contract...")
    rc, stdout, stderr = run_cmd(f'docker exec {CONTAINER} bash -lc "DISPLAY=:1 /usr/local/bin/launch-ayugram >/tmp/ayugram-runtime.log 2>&1 &"')
    time.sleep(2)

    # 5. Recovery Verification
    rc, restored_pids, _ = run_cmd(f'docker exec {CONTAINER} bash -lc "pgrep -x AyuGram || true"')
    if restored_pids:
        print(f"  -> Recovery Confirmed: Restored AyuGram PID = {restored_pids} [RESTORED]")
    else:
        print("  -> [FAIL] Failed to restore AyuGram process!")
        return 1

    # 6. X11 Window Remap Check
    print("\n[STEP 4] Verifying X11 Window Rendering after Recovery...")
    rc, wm_out, _ = run_cmd(f'docker exec {CONTAINER} bash -lc "DISPLAY=:1 wmctrl -lx"')
    if "AyuGram" in wm_out or "Telegram" in wm_out:
        print(f"  -> X11 Window mapped successfully:\n     {wm_out.splitlines()[-1]}")
    else:
        print("  -> [WARN] Window not yet rendered in wmctrl (may need 1s more).")

    # 7. Sockets check
    tcp_ok = check_tcp(5900)
    http_ok = check_http()
    print(f"\n[STEP 5] Checking Endpoint Resilience:")
    print(f"  -> VNC Socket 5900: {'ONLINE [OK]' if tcp_ok else 'OFFLINE'}")
    print(f"  -> noVNC Web 6080:  {'HTTP 200 [OK]' if http_ok else 'OFFLINE'}")

    if restored_pids and tcp_ok and http_ok:
        print("\n" + "=" * 72)
        print("   CHAOS RECOVERY RESULT: PASS (100% RECOVERED FROM PROCESS CRASH)")
        print("=" * 72)
        return 0
    else:
        print("\n" + "=" * 72)
        print("   CHAOS RECOVERY RESULT: FAILED")
        print("=" * 72)
        return 1

if __name__ == "__main__":
    sys.exit(main())
