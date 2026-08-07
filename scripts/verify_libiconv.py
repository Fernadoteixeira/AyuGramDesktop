#!/usr/bin/env python3
"""Verify that the libiconv dependency is pinned with a valid SHA-256 checksum.

This script is invoked by the `.github/workflows/security-checks.yml` CI
workflow (the "Verify libiconv checksum" step). It enforces a supply-chain
security gate: the libiconv tarball consumed by
`Telegram/build/prepare/prepare.py` must declare a non-empty, immutable
SHA-256 digest so a tampered or replaced upstream artifact cannot silently
slip into the build.

Behaviour
---------
* Static check (default, network-free, CI-safe):
    Reads `Telegram/build/prepare/prepare.py`, locates the `stage('libiconv', ...)`
    block, extracts the `SHA256=<value>` assignment and validates that the
    value is exactly 64 lowercase hexadecimal characters (the SHA-256 format).
    Exits 0 when the hash is present and well-formed, 1 otherwise.

* Optional network check (when passed `--download`):
    Additionally downloads the libiconv tarball from the pinned HTTPS URL,
    recomputes its SHA-256, and compares it to the pinned digest. Exits 1 on
    any mismatch, download failure, or hash format error.

Exit codes
----------
    0 - verification passed (hash present, valid format, and — with
        `--download` — matches the downloaded artifact)
    1 - verification failed (hash missing, empty, malformed, or — with
        `--download` — did not match the downloaded artifact)

This script depends only on the Python 3 standard library.
"""

import argparse
import hashlib
import os
import re
import sys

# Repository layout: this script lives in <repo>/scripts/, so the repo root is
# one directory up from the script's own location.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, os.pardir))
PREPARE_PY = os.path.join(REPO_ROOT, "Telegram", "build", "prepare", "prepare.py")

# A SHA-256 digest is 64 lowercase hex characters.
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

# Anchors used to locate the libiconv stage within prepare.py.
LIBICONV_STAGE_RE = re.compile(r"stage\(\s*['\"]libiconv['\"]", re.IGNORECASE)


def extract_pinned_hash(prepare_path):
    """Return the pinned libiconv SHA-256 string found in prepare.py.

    The prepare.py file declares stages via stage('libiconv', <triple-quoted
    block>). Inside that block, the hash is assigned as `SHA256=<64 hex chars>`
    on its own line. We parse the file to find the libiconv stage and then
    extract the first `SHA256=...` assignment that follows it.

    Returns the hash string (lowercased) or None if not found.
    """
    try:
        with open(prepare_path, "r", encoding="utf-8") as handle:
            content = handle.read()
    except OSError as exc:
        print(f"FAIL: could not read {prepare_path}: {exc}")
        return None

    # Split into lines so we can scan from the libiconv stage header onward.
    lines = content.splitlines()

    in_libiconv_stage = False
    brace_depth = 0
    hash_pattern = re.compile(r"^\s*SHA256\s*=\s*([0-9a-fA-F]{64})\s*$")

    for line in lines:
        if not in_libiconv_stage:
            if LIBICONV_STAGE_RE.search(line):
                in_libiconv_stage = True
                # Track parentheses so we know when the stage() call ends.
                brace_depth = line.count("(") - line.count(")")
            continue

        # We are inside the libiconv stage() call body.
        match = hash_pattern.match(line)
        if match:
            return match.group(1).lower()

        # Update parenthesis depth; if it returns to zero, the stage() call
        # has closed without a hash — give up.
        brace_depth += line.count("(") - line.count(")")
        if brace_depth <= 0:
            return None

    return None


def extract_pinned_version(prepare_path):
    """Return the pinned libiconv version string (e.g. '1.18') if present."""
    try:
        with open(prepare_path, "r", encoding="utf-8") as handle:
            content = handle.read()
    except OSError:
        return None

    lines = content.splitlines()
    in_libiconv_stage = False
    version_pattern = re.compile(r"^\s*VERSION\s*=\s*([\w.\-]+)\s*$")

    for line in lines:
        if not in_libiconv_stage:
            if LIBICONV_STAGE_RE.search(line):
                in_libiconv_stage = True
            continue
        match = version_pattern.match(line)
        if match:
            return match.group(1)
    return None


def download_and_verify(url, expected_sha256):
    """Download `url` and confirm its SHA-256 matches `expected_sha256`.

    Returns True on match, False otherwise (including download errors).
    """
    try:
        import urllib.request
    except ImportError:
        print("FAIL: urllib.request unavailable; cannot perform network check.")
        return False

    try:
        with urllib.request.urlopen(url, timeout=60) as response:  # noqa: S310
            data = response.read()
    except Exception as exc:  # noqa: BLE001 - network failures are user-facing
        print(f"FAIL: download failed for {url}: {exc}")
        return False

    actual = hashlib.sha256(data).hexdigest()
    if actual.lower() != expected_sha256.lower():
        print(f"FAIL: checksum mismatch for {url}")
        print(f"       expected: {expected_sha256}")
        print(f"       actual:   {actual}")
        return False
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Verify the libiconv SHA-256 pin in prepare.py."
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="Optionally download the tarball and confirm the hash matches "
        "(requires network). Without this flag, only a static format check "
        "is performed.",
    )
    args = parser.parse_args()

    if not os.path.isfile(PREPARE_PY):
        print(f"FAIL: prepare.py not found at {PREPARE_PY}")
        return 1

    pinned_hash = extract_pinned_hash(PREPARE_PY)
    if pinned_hash is None:
        print(
            "FAIL: no SHA256 assignment found inside the libiconv stage of "
            f"{PREPARE_PY}. The dependency appears to be unpinned."
        )
        return 1

    if not SHA256_RE.match(pinned_hash):
        print(
            "FAIL: libiconv SHA256 is present but not valid SHA-256 format "
            f"(expected 64 lowercase hex chars, got: {pinned_hash!r})"
        )
        return 1

    print(f"PASS: libiconv SHA-256 is pinned and valid: {pinned_hash}")

    if args.download:
        version = extract_pinned_version(PREPARE_PY)
        if not version:
            print("FAIL: --download requested but VERSION not found in stage")
            return 1
        url = f"https://ftp.gnu.org/gnu/libiconv/libiconv-{version}.tar.gz"
        print(f"INFO: downloading and verifying {url}")
        if not download_and_verify(url, pinned_hash):
            return 1
        print(f"PASS: downloaded tarball SHA-256 matches pin for libiconv {version}")

    return 0


if __name__ == "__main__":
    sys.exit(main())