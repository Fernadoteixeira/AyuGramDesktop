#!/usr/bin/env python3
"""Resolve mutable git refs to commit SHAs via `git ls-remote`.

One-shot helper for the SEC-331/332/333 audit.  Not part of the build.
Prints TSV: name<TAB>url<TAB>ref<TAB>sha<TAB>type
where type is one of: annotated-tag, lightweight-tag, branch, HEAD, UNRESOLVED.
"""
import shutil
import subprocess

# (name, url, ref)
REFS = [
    ("xz",            "https://github.com/tukaani-project/xz.git",     "v5.4.5"),
    ("zlib",          "https://github.com/madler/zlib.git",            "v1.3.1"),
    ("mozjpeg",       "https://github.com/mozilla/mozjpeg.git",       "v4.1.5"),
    ("openssl",       "https://github.com/openssl/openssl",            "openssl-3.5.7"),
    ("opus",          "https://github.com/xiph/opus.git",             "v1.5.2"),
    ("dav1d",         "https://code.videolan.org/videolan/dav1d.git",  "1.5.3"),
    ("openh264",      "https://github.com/cisco/openh264.git",        "v2.6.0"),
    ("libavif",       "https://github.com/AOMediaCodec/libavif.git",   "v1.3.0"),
    ("libde265",      "https://github.com/strukturag/libde265.git",    "v1.0.16"),
    ("libwebp",       "https://github.com/webmproject/libwebp.git",    "v1.6.0"),
    ("libheif",       "https://github.com/strukturag/libheif.git",    "v1.21.2"),
    ("libjxl",        "https://github.com/libjxl/libjxl.git",          "v0.11.2"),
    ("libvpx",        "https://github.com/webmproject/libvpx.git",    "v1.14.1"),
    ("Little-CMS",    "https://github.com/mm2/Little-CMS.git",        "lcms2.16"),
    ("nv-codec-headers","https://github.com/FFmpeg/nv-codec-headers.git","n12.1.14.0"),
    ("boost-regex",   "https://github.com/boostorg/regex.git",        "boost-1.83.0"),
    ("FFmpeg",        "https://github.com/FFmpeg/FFmpeg.git",         "n6.1.6"),
    ("googletest",    "https://github.com/google/googletest",         "release-1.11.0"),
    ("ada",           "https://github.com/ada-url/ada.git",            "v3.2.4"),
    ("protobuf",      "https://github.com/protocolbuffers/protobuf",   "v21.9"),
    ("gas-preprocessor","https://github.com/FFmpeg/gas-preprocessor", "HEAD"),
]


def ls_remote(url, flags, patterns):
    """Run `git ls-remote <flags> <url> <patterns>`, return stdout text."""
    git_bin = shutil.which("git") or "git"
    try:
        out = subprocess.run(
            [git_bin, "ls-remote"] + flags + [url] + patterns,
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return None
    if out.returncode != 0:
        return None
    return out.stdout


def _first_sha(text, refpath):
    """Return the SHA for the first line whose ref path == refpath, or None."""
    for line in (text or "").splitlines():
        if not line.strip():
            continue
        sha, _, rp = line.partition("\t")
        if rp == refpath:
            return sha
    return None


def classify(url, ref):
    """Return (commit_sha, type) or (None, 'UNRESOLVED').

    Uses full refspecs so the `^{}` deref line of annotated tags is returned:
    `git ls-remote <url> <pattern>` drops `^{}` entries when a short pattern
    is given, so we query the explicit refpaths instead.
    """
    # 1. Annotated tag: dereferenced commit.
    deref = ls_remote(url, [], [f"refs/tags/{ref}^{{}}"])
    if deref and deref.strip():
        sha = _first_sha(deref, f"refs/tags/{ref}^{{}}")
        if sha:
            return (sha, "annotated-tag")

    # 2. Lightweight tag: tag ref points directly at a commit.
    tag = ls_remote(url, [], [f"refs/tags/{ref}"])
    if tag and tag.strip():
        sha = _first_sha(tag, f"refs/tags/{ref}")
        if sha:
            return (sha, "lightweight-tag")

    # 3. Branch head.
    head = ls_remote(url, [], [f"refs/heads/{ref}"])
    if head and head.strip():
        sha = _first_sha(head, f"refs/heads/{ref}")
        if sha:
            return (sha, "branch")

    # 4. HEAD (default branch).
    if ref == "HEAD":
        plain = ls_remote(url, [], ["HEAD"])
        if plain and plain.strip():
            sha = _first_sha(plain, "HEAD")
            if sha:
                return (sha, "HEAD")

    return (None, "UNRESOLVED")


def main():
    print("name\turl\tref\tsha\ttype")
    for name, url, ref in REFS:
        sha, typ = classify(url, ref)
        print(f"{name}\t{url}\t{ref}\t{sha or 'UNRESOLVED'}\t{typ}")


if __name__ == "__main__":
    main()