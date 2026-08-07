# Security Regression Test Manifest

Phase V6 — Security Regression Matrix for AyuGramDesktop.

This manifest documents all security regression test files, their coverage,
expected results, and how to execute them once the compile blocker
(AGENTS.md "Avoid building the project") is lifted.

---

## Test File Inventory

| # | File | Lines | Test Cases | Classification |
|---|------|-------|------------|----------------|
| 1 | `Telegram/SourceFiles/storage/details/storage_file_utilities_kdf_test.cpp` | ~170 | 7 | VERIFIED_STATIC / BLOCKED_RUNTIME_VALIDATION |
| 2 | `Telegram/SourceFiles/ayu/data/ayu_database_test.cpp` | ~210 | 8 | VERIFIED_STATIC / BLOCKED_RUNTIME_VALIDATION |
| 3 | `session-state/.../v3/traversal_harness.cpp` (external) | ~310 | 31 | RUNTIME_VALIDATED (compiled & run via WSL g++ 15.2.0) |

---

## 1. Traversal Harness (V3) — RUNTIME VALIDATED

**Source:** `session-state/3d76d367-f6a9-48d9-b59f-f06fbee5d507/files/v3/traversal_harness.cpp`

**What it tests:** Path-traversal sanitization logic extracted from
`Telegram/SourceFiles/ayu/features/forward/ayu_sync.cpp` (`filePath()` function).
The harness replicates `base::FileNameFromUserString` (both generic and Windows
layers) verbatim and tests the predicate chain:
`!safeName.isEmpty() && !safeName.contains("..") && fullPath.startsWith(folderPath + '/')`.

**How to run:**
```bash
g++ -std=c++17 -o harness.exe traversal_harness.cpp
./harness.exe
```

**Latest run results (2026-08-07):**
- **Compiler:** g++ (Ubuntu 15.2.0-16ubuntu1) 15.2.0 via WSL
- **Command:** `g++ -std=c++17 -o /tmp/harness.exe /tmp/traversal_harness.cpp && /tmp/harness.exe`
- **Exit code:** 0
- **Result:** 31 passed, 0 failed

**Coverage:**
| Category | Cases | Examples |
|----------|-------|---------|
| Benign filenames | 7 | `photo.png`, `relatório final.pdf`, `a/b`, `x.` |
| Unix traversal | 1 | `../../etc/cron.d/x` → FALLBACK |
| Windows traversal | 1 | `..\..\AppData\...\Startup\x.exe` → FALLBACK |
| Mixed separators | 1 | `..\/..\/etc/x` → FALLBACK |
| Absolute paths | 3 | `/etc/passwd` → `_etc_passwd` (in-folder) |
| RTLO neutralization | 1 | `exe‮gnp.txt` → `exe_gnp.txt` |
| Control chars | 1 | `evil\x01\x1Ffile.exe` → `evil__file.exe` |
| Reserved names | 2 | `CON.txt` → `_CON.txt`, `NUL` → `_NUL` |
| Bad extensions | 1 | `evil.lnk` → `evil.lnk.download` |
| Dot/empty edge cases | 5 | `..`, `...`, empty, `/`, `\` |
| Over-blocking false positives | 3 | `.._evil`, `report..final.pdf` |
| Containment prefix proofs | 4 | prefix-collision blocked by trailing `/` |
| Fail-safe relative folder | 1 | `dl` (no trailing slash) → FALLBACK |

---

## 2. KDF Test File — VERIFIED_STATIC

**File:** `Telegram/SourceFiles/storage/details/storage_file_utilities_kdf_test.cpp`

**What it tests:** The scrypt/PBKDF2 KDF branch logic in
`storage_file_utilities.cpp` `CreateLocalKey()` (lines 306-386) and
`CreateLegacyLocalKey()` (lines 366-386).

**Key fix being verified:** When the salt marker is `0x02` (kKdfVersionScrypt)
and the scrypt branch fails, the function must return `nullptr` — it must NOT
silently fall through to the PBKDF2 branch below. Before the fix, scrypt
failure would continue into PBKDF2, producing a weak key without indication.

**Test cases:**

| # | Test Name | Description | Expected Result |
|---|-----------|-------------|-----------------|
| 1 | `ScryptSuccess` | 0x02 marker + non-empty passcode | Non-null, non-zero key |
| 2 | `ScryptFailure` | 0x02 marker + empty passcode | nullptr (no PBKDF2 fallback) |
| 3 | `UnknownMarker` | 0x03 marker + passcode | Non-null key via PBKDF2 fallback |
| 4 | `RestartUnlock` | Same (passcode, salt) called twice | Identical keys (deterministic) |
| 5 | `LegacyUpgrade` | 0x01 marker + passcode | Non-null key via PBKDF2 (backward compat) |
| 6 | `MixedState` | 0x02 marker + empty passcode vs 0x01 marker | scryptKey == nullptr, pbkdf2Key != nullptr, keys differ |
| 7 | `LegacyLocalKeyCompatibility` | `CreateLegacyLocalKey` with SHA1 | Non-null, non-zero key |

**How to run (once unblocked):**
```bash
# Add to CMakeLists.txt as a separate executable target linked against:
#   mtproto_auth_key, base, openssl (libcrypto), Qt::Core
cmake --build out --target storage_file_utilities_kdf_test
./out/storage_file_utilities_kdf_test
```

**Classification rationale:** The test calls `CreateLocalKey` and
`CreateLegacyLocalKey` directly, which depend on OpenSSL (`EVP_PBE_scrypt`,
`PKCS5_PBKDF2_HMAC`), `MTP::AuthKey`, `bytes::make_span`, and Qt's
`QByteArray`. These are project-internal dependencies that cannot be satisfied
without the full build environment. The test logic has been statically verified
against the source — each assertion matches the code path in
`storage_file_utilities.cpp`.

---

## 3. SQLCipher Test File — VERIFIED_STATIC

**File:** `Telegram/SourceFiles/ayu/data/ayu_database_test.cpp`

**What it tests:** The SQLCipher encryption implementation in
`ayu_database.cpp`, including:
- The `on_open` hook in `storage()` (line 350) that calls `applyCodecKey(db)`
  before any PRAGMA statement
- `migratePlaintextDatabase()` (line 260) — atomic plaintext → encrypted migration
- `retentionAllowed()` (line 206) — write gate based on `passcodeLocked()`
- `zeroizeKey()` (line 437) — secure key wipe and state reset

**Test cases:**

| # | Test Name | Description | Expected Result |
|---|-----------|-------------|-----------------|
| 1 | `EncryptionApplied` | After `initialize()`, DB file exists but has no plaintext header | File exists, no "SQLite format 3" header |
| 2 | `KeyRequired` | DB file cannot be read as plaintext SQLite without the key | Raw file read shows no SQLite header |
| 3 | `MigrationSuccess` | Plaintext DB → encrypted DB | No plaintext header remains after init |
| 4 | `MigrationRollback` | Migration failure → plaintext DB preserved, `.enc` cleaned up | Plaintext file intact, `.enc` removed |
| 5 | `RetentionGateLocked` | `passcodeLocked() == true` → writes blocked | `getCount()` unchanged after `addEditedMessage()` |
| 6 | `RetentionGateUnlocked` | `passcodeLocked() == false` → writes allowed | `getCount()` increments by 1 |
| 7 | `ZeroizeKey` | After `zeroizeKey()`, state resets and writes blocked | `getCount()` unchanged after write attempt |
| 8 | `KeyAppliedBeforePragmas` | `on_open` hook applies key before PRAGMAs | DB is encrypted, `getCount()` returns valid value |

**How to run (once unblocked):**
```bash
# Add to CMakeLists.txt as a separate executable target linked against:
#   ayu_database, ayu_database_key, sqlite_orm, sqlite3mc, openssl, Qt::Core
# Requires cWorkingDir() to point to a writable test tdata directory.
cmake --build out --target ayu_database_test
./out/ayu_database_test
```

**Classification rationale:** The test depends on `AyuDatabase::initialize()`,
which calls `currentLocalKey()` → `Core::App().domain().active().local()`,
requiring a fully initialized Telegram Desktop application context with a
running domain and active session. Additionally, `retentionAllowed()` checks
`Core::App().passcodeLocked()` and `Core::IsAppLaunched()`, which require the
application event loop. The internal state variables (`g_state`, `g_databaseKey`)
are in an anonymous namespace, so they cannot be directly inspected — tests
verify observable behavior through the public API. All test logic has been
statically verified against the source.

---

## Classification Definitions

| Classification | Meaning |
|---------------|---------|
| **RUNTIME_VALIDATED** | Compiled and executed successfully. Results recorded. |
| **VERIFIED_STATIC** | Test logic reviewed against source code. Each assertion matches a specific code path. Not compiled. |
| **BLOCKED_RUNTIME_VALIDATION** | Cannot be compiled due to AGENTS.md "Avoid building the project" constraint or missing test infrastructure. |

---

## Acceptance Criteria Status

- [x] Traversal harness rerun: COMMAND, EXIT_CODE, OUTPUT recorded (31/31 PASS, exit 0)
- [x] KDF test file created with 7 deterministic test cases (6 required + 1 bonus)
- [x] SQLCipher test file created with 8 test cases
- [x] Security test manifest created
- [x] All test files use correct coding style (tabs, auto, no single-line comments)