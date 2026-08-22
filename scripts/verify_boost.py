#!/usr/bin/env python3
"""Verify that the Boost dependency is pinned with a valid SHA-256 checksum.

This script is invoked by the `.github/workflows/security-checks.yml` CI
workflow (the "Verify Boost checksum" step). It enforces a supply-chain
security gate: the Boost source tarball consumed by the Linux build image
defined in `Telegram/build/docker/centos_env/Dockerfile` must declare a
non-empty, immutable SHA-256 digest so a tampered or replaced upstream
artifact cannot silently slip into the build.

Behaviour
---------
* Static check (default, network-free, CI-safe):
    Reads the Dockerfile, locates the `boost` build stage, extracts the
    `BOOST_SHA256=<value>` ENV assignment and validates that the value is
    exactly 64 lowercase hexadecimal characters (the SHA-256 format). It also
    confirms the `sha256sum -c` verification line is present in that stage so
    the pin is actually enforced at build time. Exits 0 when everything is in
    order, 1 otherwise.

* Optional network check (when passed `--download`):
    Additionally downloads the Boost tarball from the pinned HTTPS URL,
    recomputes its SHA-256, and compares it to the pinned digest. Exits 1 on
    any mismatch, download failure, or hash format error.

Exit codes
----------
    0 - verification passed (hash present, valid format, sha256sum check
        present, and — with `--download` — matches the downloaded artifact)
    1 - verification failed (hash missing, empty, malformed, sha256sum check
        missing, or — with `--download` — did not match the downloaded
        artifact)

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
DOCKERFILE = os.path.join(
    REPO_ROOT, "Telegram", "build", "docker", "centos_env", "Dockerfile"
)

# A SHA-256 digest is 64 lowercase hex characters.
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

# Anchors used to locate the boost build stage within the Dockerfile.
BOOST_STAGE_RE = re.compile(r"^\s*FROM\s+\S+\s+AS\s+boost\b", re.IGNORECASE)


def extract_pinned_hash(dockerfile_path):
    """Return the pinned Boost SHA-256 string and whether a sha256sum check
    exists in the same stage.

    The Dockerfile declares a multi-stage build with `FROM ... AS boost`.
    Inside that stage, the hash is set as
    `ENV BOOST_SHA256=<64 hex chars>`. We scan the boost stage lines for the
    ENV assignment and for a `sha256sum -c` (or equivalent) verification step.

    Returns a tuple (hash_lower_or_None, has_sha256sum_check_bool).
    """
    try:
        with open(dockerfile_path, "r", encoding="utf-8") as handle:
            content = handle.read()
    except OSError as exc:
        print(f"FAIL: could not read {dockerfile_path}: {exc}")
        return None, False

    lines = content.splitlines()

    in_boost_stage = False
    hash_pattern = re.compile(
        r"^\s*ENV\s+BOOST_SHA256\s*=\s*([0-9a-fA-F]{64})\s*$", re.IGNORECASE
    )
    # A new `FROM ... AS <name>` line starts a new stage, ending the boost one.
    next_stage_re = re.compile(r"^\s*FROM\s+", re.IGNORECASE)

    pinned_hash = None
    has_sha256sum_check = False

    for line in lines:
        if not in_boost_stage:
            if BOOST_STAGE_RE.match(line):
                in_boost_stage = True
            continue

        # If we hit another FROM line, the boost stage has ended.
        if next_stage_re.match(line) and not BOOST_STAGE_RE.match(line):
            break

        if pinned_hash is None:
            match = hash_pattern.match(line)
            if match:
                pinned_hash = match.group(1).lower()

        if re.search(r"sha256sum\s+-c", line, re.IGNORECASE):
            has_sha256sum_check = True

    return pinned_hash, has_sha256sum_check


def extract_pinned_url(dockerfile_path):
    """Return the pinned Boost download URL from the boost stage, if present."""
    try:
        with open(dockerfile_path, "r", encoding="utf-8") as handle:
            content = handle.read()
    except OSError:
        return None

    lines = content.splitlines()
    in_boost_stage = False
    url_pattern = re.compile(r"https?://\S+boost\S*\.tar\.gz", re.IGNORECASE)
    next_stage_re = re.compile(r"^\s*FROM\s+", re.IGNORECASE)

    for line in lines:
        if not in_boost_stage:
            if BOOST_STAGE_RE.match(line):
                in_boost_stage = True
            continue
        if next_stage_re.match(line) and not BOOST_STAGE_RE.match(line):
            break
        match = url_pattern.search(line)
        if match:
            return match.group(0)
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

    if not url.startswith("https://"):
        print(f"FAIL: unexpected non-HTTPS URL: {url}")
        return False

    try:
        with urllib.request.urlopen(url, timeout=60) as response:  # nosec B310
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
        description="Verify the Boost SHA-256 pin in the build Dockerfile."
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="Optionally download the tarball and confirm the hash matches "
        "(requires network). Without this flag, only a static format check "
        "is performed.",
    )
    args = parser.parse_args()

    if not os.path.isfile(DOCKERFILE):
        print(f"FAIL: Dockerfile not found at {DOCKERFILE}")
        return 1

    pinned_hash, has_sha256sum_check = extract_pinned_hash(DOCKERFILE)

    if pinned_hash is None:
        print(
            "FAIL: no BOOST_SHA256 ENV assignment found inside the boost "
            f"stage of {DOCKERFILE}. The dependency appears to be unpinned."
        )
        return 1

    if not SHA256_RE.match(pinned_hash):
        print(
            "FAIL: BOOST_SHA256 is present but not valid SHA-256 format "
            f"(expected 64 lowercase hex chars, got: {pinned_hash!r})"
        )
        return 1

    print(f"PASS: Boost SHA-256 is pinned and valid: {pinned_hash}")

    if not has_sha256sum_check:
        print(
            "FAIL: boost stage declares BOOST_SHA256 but contains no "
            "`sha256sum -c` verification step — the pin is not enforced at "
            "build time."
        )
        return 1
    print("PASS: boost stage enforces the pin via `sha256sum -c`")

    if args.download:
        url = extract_pinned_url(DOCKERFILE)
        if not url:
            print("FAIL: --download requested but URL not found in stage")
            return 1
        print(f"INFO: downloading and verifying {url}")
        if not download_and_verify(url, pinned_hash):
            return 1
        print("PASS: downloaded tarball SHA-256 matches Boost pin")

    return 0


if __name__ == "__main__":
    sys.exit(main())