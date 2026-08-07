# Mutable Git References Resolution Report

**Audit:** Security 360° — SEC-331 / SEC-332 / SEC-333
**Scope:** `Telegram/build/prepare/prepare.py`, `Telegram/build/docker/centos_env/Dockerfile`
**Detector:** `scripts/check_mutable_refs.py`
**Resolution method:** `git ls-remote` (no cloning) against each remote origin.
**Date:** 2026-08-07

> **Note on tag-object SHAs.** For *annotated* tags, `git ls-remote --tags <url> <pattern>`
> returns the **tag object** SHA on the `refs/tags/<ref>` line and the **dereferenced commit**
> on the `refs/tags/<ref>^{}` line. The build file sometimes checks out the tag-object SHA
> (e.g. zlib `925af44f…`, mozjpeg `38f37cf9…`, opus `5ec2f3c9…`, nv-codec-headers
> `145d4ca8…`). `git checkout <tag-object-sha>` auto-dereferences to the underlying commit,
> so those stages are still deterministically pinned. The "resolved SHA" column below lists
> the **commit** (the `^{}` value) so it is directly comparable; the "matches file checkout"
> status reflects this dereference.

## 1. Findings table

25 mutable references were detected. All resolvable refs were resolved via `git ls-remote`
to a 40-hex commit SHA (or `HEAD` for the one bare clone). No remote was unreachable.

| # | File | Line | Dependency | Remote origin (SEC-333) | Original ref | Resolved commit SHA | Tag type (SEC-332) | Status |
|---|------|-----:|------------|--------------------------|--------------|----------------------|--------------------|--------|
| 1 | prepare.py | 525 | xz | https://github.com/tukaani-project/xz.git | `v5.4.5` | `49053c0a649f4c8bd2b8d97ce915f401fbc0f3d9` | annotated-tag | pinned by checkout @527 (matches) |
| 2 | prepare.py | 537 | zlib | https://github.com/madler/zlib.git | `v1.3.1` | `51b7f2abdade71cd9bb0e7a373ef2610ec6f9daf` | annotated-tag | pinned by checkout @539 (tag-obj `925af44f` → this commit) |
| 3 | prepare.py | 559 | mozjpeg | https://github.com/mozilla/mozjpeg.git | `v4.1.5` | `6c9f0897afa1c2738d7222a0a9ab49e8b536a267` | annotated-tag | pinned by checkout @561 (tag-obj `38f37cf9` → this commit) |
| 4 | prepare.py | 597 | openssl | https://github.com/openssl/openssl | `openssl-3.5.7` | `8cf17aaeb4599f8af87fefd810b5b5fee90fe69e` | annotated-tag | pinned by checkout @599 (matches) |
| 5 | prepare.py | 645 | opus | https://github.com/xiph/opus.git | `v1.5.2` | `ddbe48383984d56acd9e1ab6a090c54ca6b735a6` | annotated-tag | pinned by checkout @647 (tag-obj `5ec2f3c9` → this commit) |
| 6 | prepare.py | 718 | gas-preprocessor | https://github.com/FFmpeg/gas-preprocessor | *(bare clone, default `HEAD`)* | `ac1836309c2e77023c228b7184485597286289d3` | HEAD (branch tip) | **UNPINNED — no checkout** |
| 7 | prepare.py | 726 | dav1d | https://code.videolan.org/videolan/dav1d.git | `1.5.3` | `b546257f770768b2c88258c533da38b91a06f737` | annotated-tag | pinned by checkout @728 (matches) |
| 8 | prepare.py | 792 | openh264 | https://github.com/cisco/openh264.git | `v2.6.0` | `652bdb7719f30b52b08e506645a7322ff1b2cc6f` | lightweight-tag | pinned by checkout @794 (matches) |
| 9 | prepare.py | 851 | libavif | https://github.com/AOMediaCodec/libavif.git | `v1.3.0` | `1aadfad932c98c069a1204261b1856f81f3bc199` | annotated-tag | pinned by checkout @853 (matches) |
| 10 | prepare.py | 881 | libde265 | https://github.com/strukturag/libde265.git | `v1.0.16` | `7ba65889d3d6d8a0d99b5360b028243ba843be3a` | lightweight-tag | pinned by checkout @883 (matches) |
| 11 | prepare.py | 914 | libwebp | https://github.com/webmproject/libwebp.git | `v1.6.0` | `4fa21912338357f89e4fd51cf2368325b59e9bd9` | annotated-tag | pinned by checkout @916 (matches) |
| 12 | prepare.py | 954 | libheif | https://github.com/strukturag/libheif.git | `v1.21.2` | `62f1b8c76ed4d8305071fdacbe74ef9717bacac5` | lightweight-tag | pinned by checkout @956 (matches) |
| 13 | prepare.py | 1015 | libjxl | https://github.com/libjxl/libjxl.git | `v0.11.2` | `332feb17d17311c748445f7ee75c4fb55cc38530` | lightweight-tag | pinned by checkout @1017 (matches) |
| 14 | prepare.py | 1060 | libvpx | https://github.com/webmproject/libvpx.git | *(bare clone)* | `12f3a2ac603e8f10742105519e0cd03c3b8f71dd` (from `v1.14.1`) | annotated-tag | **UNPINNED — bare clone, then mutable-tag checkout** |
| 15 | prepare.py | 1063 | libvpx | https://github.com/webmproject/libvpx.git | `v1.14.1` | `12f3a2ac603e8f10742105519e0cd03c3b8f71dd` | annotated-tag | **UNPINNED — checkout by mutable tag, not SHA** |
| 16 | prepare.py | 1122 | Little-CMS | https://github.com/mm2/Little-CMS.git | `lcms2.16` | `453bafeb85b4ef96498866b7a8eadcc74dff9223` | lightweight-tag | pinned by checkout @1124 (matches) |
| 17 | prepare.py | 1160 | nv-codec-headers | https://github.com/FFmpeg/nv-codec-headers.git | `n12.1.14.0` | `1889e62e2d35ff7aa9baca2bceb14f053785e6f1` | annotated-tag | pinned by checkout @1163 (tag-obj `145d4ca8` → this commit) |
| 18 | prepare.py | 1166 | boost-regex | https://github.com/boostorg/regex.git | `boost-1.83.0` | `4cbcd3078e6ae10d05124379623a1bf03fcb9350` | lightweight-tag | pinned by checkout @1169 (matches) |
| 19 | prepare.py | 1172 | FFmpeg | https://github.com/FFmpeg/FFmpeg.git | `n6.1.6` | `f1e3a2bf7a2f2cde936d1ed97f09a26853d20125` | annotated-tag | pinned by checkout @1175 (matches) |
| 20 | prepare.py | 1388 | googletest | https://github.com/google/googletest | `release-1.11.0` | `e2239ee6043f73722e7aa812a459f54a28552929` | lightweight-tag | pinned by checkout @1389 (matches) — stackwalk stage |
| 21 | prepare.py | 1405 | googletest | https://github.com/google/googletest | `release-1.11.0` | `e2239ee6043f73722e7aa812a459f54a28552929` | lightweight-tag | pinned by checkout @1406 (matches) — breakpad stage |
| 22 | prepare.py | 1517 | qt5 | https://github.com/qt/qt5.git | `v$QT-lts-lgpl` | *(runtime-variable)* | shell variable (`$QT`) | legitimately runtime-variable |
| 23 | prepare.py | 1608 | qt5 | https://github.com/qt/qt5.git | `""" + branch + """` (Python `branch` var) | *(runtime-variable)* | Python variable | legitimately runtime-variable |
| 24 | prepare.py | 1799 | ada | https://github.com/ada-url/ada.git | `v3.2.4` | `010f7c45aeaff1205452e7da2df8702cf725fb3e` | lightweight-tag | pinned by checkout @1801 (matches) |
| 25 | prepare.py | 1822 | protobuf | https://github.com/protocolbuffers/protobuf | `v21.9` | `90b73ac3f0b10320315c2ca0d03a5a9b095d2f66` | annotated-tag | **UNPINNED — no protobuf checkout (only abseil pinned)** |

The `centos_env/Dockerfile` contains **no** mutable references — every dependency there is
fetched by `git fetch --depth=1 origin <40-hex-SHA>` + `git reset --hard FETCH_HEAD`
(SEC-331 already satisfied for that file). It is not listed in the table because the detector
reported zero findings for it.

## 2. Recommendations

### 2a. Genuinely unpinned — pin now (3 dependencies, 4 findings)

These stages rely entirely on a mutable ref (tag or default-branch `HEAD`) with **no**
subsequent immutable `git checkout <SHA>`. A tag/branch move by the upstream owner would
silently change the built artifact. These are the real supply-chain risk.

| Dep | Lines | Current | Recommended pin (resolved SHA) |
|-----|-------|---------|--------------------------------|
| gas-preprocessor | 718 | bare `git clone` (no checkout) | add `cd gas-preprocessor && git checkout ac1836309c2e77023c228b7184485597286289d3` |
| libvpx | 1060, 1063 | bare clone + `git checkout v1.14.1` | replace `git checkout v1.14.1` → `git checkout 12f3a2ac603e8f10742105519e0cd03c3b8f71dd` |
| protobuf | 1822 | `git clone -b v21.9` (no protobuf checkout) | add `cd protobuf && git checkout 90b73ac3f0b10320315c2ca0d03a5a9b095d2f66` (after the `cd protobuf` on line 1823) |

### 2b. Already effectively pinned — hygiene improvement (19 findings, 17 distinct deps)

Each of these does `git clone -b <mutable-tag>` **followed by** `git checkout <40-hex-SHA>`.
The checkout makes the build deterministic today, so the supply-chain risk is low. For full
defense-in-depth, the mutable tag can be removed from the clone command:

- Replace `git clone -b <tag> <url>` + `git checkout <SHA>` with
  `git clone <url>` + `cd <dir>` + `git checkout <SHA>` (or `git clone -b <SHA> <url>`).
- This eliminates the mutable tag reference entirely while preserving the existing pin.

Affected dependencies: xz, zlib, mozjpeg, openssl, opus, dav1d, openh264, libavif, libde265,
libwebp, libheif, libjxl, Little-CMS, nv-codec-headers, boost-regex, FFmpeg, googletest (×2),
ada.

### 2c. Legitimately runtime-variable (2 findings)

| Dep | Lines | Why it cannot be resolved statically |
|-----|-------|--------------------------------------|
| qt5 | 1517 | `v$QT-lts-lgpl` — the branch is derived from the shell variable `$QT` (Qt LTS builds, e.g. `v6.2.x-lts-lgpl`). The Qt version is a build-time parameter. |
| qt5 | 1608 | `""" + branch + """` — the branch is built from the Python variable `branch = 'v' + qt + ('-lts-lgpl' if …)`. Same rationale. |

These are intentional: Qt is intentionally versioned via a build parameter and the qt5 repo is
consumed via pinned submodules (`git submodule update --init …`). **Recommendation:** instead
of pinning the qt5 superproject branch, pin the *submodule* commits (qtbase, qtimageformats,
qtsvg) to SHAs, which is where the actual built code lives. Out of scope for this research task
— flagged as a follow-up.

## 3. Summary

| Metric | Count |
|--------|------:|
| Total mutable references detected | 25 |
| Resolved to a commit SHA via `git ls-remote` | 21 distinct refs (covering 23 findings) |
| Unresolved (remote unreachable) | 0 |
| Legitimately runtime-variable (cannot resolve statically) | 2 (qt5 ×2) |
| Genuinely unpinned — needs SHA pinning | 3 dependencies / 4 findings (gas-preprocessor, libvpx, protobuf) |
| Already effectively pinned by a following `git checkout <SHA>` | 19 findings / 17 distinct deps |
| Annotated tags | 12 (xz, zlib, mozjpeg, openssl, opus, dav1d, libavif, libwebp, libvpx, nv-codec-headers, FFmpeg, protobuf) |
| Lightweight tags | 8 (openh264, libde265, libheif, libjxl, Little-CMS, boost-regex, googletest, ada) |
| Branch / HEAD refs | 1 (gas-preprocessor default HEAD) |

**Tag-type tally (by distinct ref, n=21):** annotated-tag = 12, lightweight-tag = 8, HEAD = 1.

**Bottom line:** The `centos_env/Dockerfile` is fully pinned (SEC-331 ✓). `prepare.py` has
25 mutable-ref findings; 21 resolve cleanly to immutable commit SHAs and 2 are legitimately
runtime-variable. Only **3 dependencies** (gas-preprocessor, libvpx, protobuf) are currently
built from a mutable ref with no SHA backstop — these should be pinned. The remaining 17
dependencies are already deterministic thanks to a following `git checkout <SHA>`; removing
the redundant mutable `-b <tag>` from those clone commands is a recommended hygiene cleanup.

## 4. Reproducibility

Resolution was produced by `scripts/resolve_refs.py` (added for this audit), which calls
`git ls-remote` with full refspecs — including `refs/tags/<ref>^{}` — so annotated tags are
correctly dereferenced to their commit. Re-run with:

```
python scripts/resolve_refs.py
```