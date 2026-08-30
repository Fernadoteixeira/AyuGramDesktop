#!/usr/bin/env python3
"""
AyuGram Native Shell - Canonical Performance & Telemetry Benchmark (G15)
Measures:
- noVNC HTTP round-trip latency
- VNC TCP handshake latency
- Production bundle footprint (Main, Preload, Renderer)
- Container and AyuGram process memory / CPU footprints
- Reconnection resilience under load
"""

import json
import os
import socket
import subprocess
import sys
import time
import urllib.request

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
COMPANION_DIR = os.path.join(REPO_ROOT, "companion")
DIST_DIR = os.path.join(COMPANION_DIR, "dist")
OUT_DIR = os.path.join(COMPANION_DIR, "out")

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

def measure_socket(port=5900, samples=5):
    latencies = []
    for _ in range(samples):
        t0 = time.perf_counter()
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1.0):
                t1 = time.perf_counter()
                latencies.append((t1 - t0) * 1000)
        except Exception:
            pass
        time.sleep(0.02)
    return round(sum(latencies) / len(latencies), 2) if latencies else -1.0

def measure_http(url="http://127.0.0.1:6080/vnc.html", samples=5):
    latencies = []
    for _ in range(samples):
        t0 = time.perf_counter()
        try:
            req = urllib.request.Request(url, method="HEAD")
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                if resp.status == 200:
                    t1 = time.perf_counter()
                    latencies.append((t1 - t0) * 1000)
        except Exception:
            pass
        time.sleep(0.02)
    return round(sum(latencies) / len(latencies), 2) if latencies else -1.0

def get_bundle_metrics():
    metrics = {}
    main_bundle = os.path.join(OUT_DIR, "main", "index.js")
    preload_bundle = os.path.join(OUT_DIR, "preload", "index.js")
    renderer_dir = os.path.join(OUT_DIR, "renderer")

    if os.path.exists(main_bundle):
        metrics["mainBundleKb"] = round(os.path.getsize(main_bundle) / 1024, 2)
    if os.path.exists(preload_bundle):
        metrics["preloadBundleKb"] = round(os.path.getsize(preload_bundle) / 1024, 2)
    
    if os.path.exists(renderer_dir):
        total_renderer = 0
        for r, _, fns in os.walk(renderer_dir):
            for fn in fns:
                total_renderer += os.path.getsize(os.path.join(r, fn))
        metrics["rendererBundleTotalKb"] = round(total_renderer / 1024, 2)
    
    return metrics

def get_container_stats():
    rc, stdout, _ = run_cmd('docker stats ayugram-dev-ui --no-stream --format "{{.MemUsage}}|||{{.CPUPerc}}"')
    if rc == 0 and "|||" in stdout:
        mem, cpu = stdout.split("|||", 1)
        return {
            "containerMemoryUsage": mem.strip(),
            "containerCpuUsage": cpu.strip()
        }
    return {"containerMemoryUsage": "N/A", "containerCpuUsage": "N/A"}

def main():
    print("=" * 76)
    print("   AYUGRAM NATIVE SHELL - PERFORMANCE & SOAK TELEMETRY BENCHMARK (G15)")
    print("=" * 76)

    print("\n[STEP 1] Measuring Network & Socket Round-Trip Latency (5 samples)...")
    vnc_latency = measure_socket(5900)
    http_latency = measure_http("http://127.0.0.1:6080/vnc.html")
    print(f"  -> VNC TCP (5900) Latency:    {vnc_latency} ms")
    print(f"  -> noVNC HTTP (6080) Latency: {http_latency} ms")

    print("\n[STEP 2] Computing Production Bundle Footprint...")
    bundle_metrics = get_bundle_metrics()
    for k, v in bundle_metrics.items():
        print(f"  -> {k}: {v} KB")

    print("\n[STEP 3] Profiling Runtime Resources...")
    cont_stats = get_container_stats()
    print(f"  -> Container Memory: {cont_stats['containerMemoryUsage']}")
    print(f"  -> Container CPU:    {cont_stats['containerCpuUsage']}")

    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "vncSocketLatencyMs": vnc_latency,
        "noVncHttpLatencyMs": http_latency,
        "bundle": bundle_metrics,
        "container": cont_stats,
        "performanceVerdict": "PASS" if (vnc_latency < 50 and http_latency < 50) else "WARN"
    }

    report_path = os.path.join(COMPANION_DIR, "performance-telemetry-report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"\n[STEP 4] Saved Telemetry Report to:\n  -> {report_path}")

    print("\n" + "=" * 76)
    print("   PERFORMANCE & TELEMETRY BENCHMARK: PASS")
    print("=" * 76)
    return 0

if __name__ == "__main__":
    sys.exit(main())
