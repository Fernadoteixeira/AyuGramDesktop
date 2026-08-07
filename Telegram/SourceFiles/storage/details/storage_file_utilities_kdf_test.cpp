/*
This file is part of Telegram Desktop,
the official desktop application for the Telegram messaging service.

For license and copyright information please follow this link:
https://github.com/telegramdesktop/tdesktop/blob/master/LEGAL
*/
/*
VERIFIED_STATIC regression tests for the KDF fix in
storage_file_utilities.cpp (CreateLocalKey scrypt/PBKDF2 branch).

STATUS:
  VERIFIED_STATIC — each test case is reviewed against the source logic at
  Telegram/SourceFiles/storage/details/storage_file_utilities.cpp lines
  306-386.  The scrypt branch (salt[0] == kKdfVersionScrypt, salt.size() > 32)
  must return nullptr on failure and must NOT silently fall back to the
  PBKDF2 branch below.  This was the original security bug: when scrypt failed
  the code continued past the scrypt block into PBKDF2, producing a weak key
  without any indication.

  BLOCKED_RUNTIME_VALIDATION — cannot be compiled per AGENTS.md
  ("Avoid building the project").  To unblock, add this translation unit to
  the Telegram CMake build alongside storage_file_utilities.cpp, link
  against mtproto_auth_key and OpenSSL, then run the resulting binary.

COVERAGE:
  1. ScryptSuccess      — 0x02 marker + non-empty passcode → valid key
  2. ScryptFailure      — scrypt branch cannot derive → nullptr, no PBKDF2
  3. UnknownMarker      — marker != 0x01 && != 0x02 → graceful PBKDF2 fallback
  4. RestartUnlock      — same (passcode, salt) pair → identical key (deterministic)
  5. LegacyUpgrade      — 0x01 marker → PBKDF2 path for backward compat
  6. MixedState         — 0x02 marker + failure → nullptr, NOT a PBKDF2 key
*/
#include "storage/details/storage_file_utilities.h"

#include "mtproto/mtproto_auth_key.h"

#include <cassert>
#include <cstring>
#include <iostream>
#include <vector>

using namespace Storage::details;

namespace {

int g_passCount = 0;
int g_failCount = 0;

void recordResult(bool ok, const char *name) {
	ok ? ++g_passCount : ++g_failCount;
	std::cout << (ok ? "PASS" : "FAIL") << " | " << name << "\n";
}

QByteArray makeSalt(std::byte marker, int payloadSize) {
	QByteArray salt;
	salt.resize(1 + payloadSize);
	salt[0] = static_cast<char>(marker);
	for (auto i = 1; i < salt.size(); ++i) {
		salt[i] = static_cast<char>(i);
	}
	return salt;
}

bool keyIsNonZero(const MTP::AuthKeyPtr &key) {
	if (!key) {
		return false;
	}
	auto span = key->data();
	auto ptr = reinterpret_cast<const unsigned char *>(span.data());
	for (auto i = 0; i < int(span.size()); ++i) {
		if (ptr[i] != 0) {
			return true;
		}
	}
	return false;
}

bool keysEqual(const MTP::AuthKeyPtr &a, const MTP::AuthKeyPtr &b) {
	if (!a || !b) {
		return false;
	}
	return a->equals(b);
}

} // namespace

static void testScryptSuccess() {
	const auto passcode = QByteArray("test-passcode");
	const auto salt = makeSalt(kKdfVersionScrypt, 48);
	const auto key = CreateLocalKey(passcode, salt);
	const auto ok = key != nullptr && keyIsNonZero(key);
	recordResult(ok, "ScryptSuccess: 0x02 marker + non-empty passcode -> valid non-zero key");
	assert(ok);
}

static void testScryptFailure() {
	const auto passcode = QByteArray();
	const auto salt = makeSalt(kKdfVersionScrypt, 48);
	const auto key = CreateLocalKey(passcode, salt);
	const auto ok = key == nullptr;
	recordResult(ok, "ScryptFailure: scrypt-marked salt with empty passcode -> nullptr, no PBKDF2 fallback");
	assert(ok);
}

static void testUnknownMarker() {
	const auto passcode = QByteArray("test-passcode");
	const auto salt = makeSalt(std::byte{0x03}, 48);
	const auto key = CreateLocalKey(passcode, salt);
	const auto ok = key != nullptr && keyIsNonZero(key);
	recordResult(ok, "UnknownMarker: 0x03 marker -> graceful PBKDF2 fallback, non-null key");
	assert(ok);
}

static void testRestartUnlock() {
	const auto passcode = QByteArray("restart-passcode");
	const auto salt = makeSalt(kKdfVersionScrypt, 48);
	const auto key1 = CreateLocalKey(passcode, salt);
	const auto key2 = CreateLocalKey(passcode, salt);
	const auto ok = keysEqual(key1, key2);
	recordResult(ok, "RestartUnlock: same (passcode, salt) -> identical key (deterministic KDF)");
	assert(ok);
}

static void testLegacyUpgrade() {
	const auto passcode = QByteArray("legacy-passcode");
	const auto salt = makeSalt(kKdfVersionPBKDF2, 48);
	const auto key = CreateLocalKey(passcode, salt);
	const auto ok = key != nullptr && keyIsNonZero(key);
	recordResult(ok, "LegacyUpgrade: 0x01 marker -> PBKDF2 path, non-null key (backward compat)");
	assert(ok);
}

static void testMixedState() {
	const auto passcode = QByteArray();
	const auto salt = makeSalt(kKdfVersionScrypt, 48);
	const auto scryptKey = CreateLocalKey(passcode, salt);
	const auto pbkdf2Salt = makeSalt(kKdfVersionPBKDF2, 48);
	const auto pbkdf2Key = CreateLocalKey(passcode, pbkdf2Salt);
	const auto ok = scryptKey == nullptr
		&& pbkdf2Key != nullptr
		&& !keysEqual(scryptKey, pbkdf2Key);
	recordResult(ok, "MixedState: 0x02 marker + failure -> nullptr, NOT the PBKDF2 key (original bug regression)");
	assert(ok);
}

static void testLegacyLocalKeyCompatibility() {
	const auto passcode = QByteArray("legacy-sha1-passcode");
	const auto salt = makeSalt(std::byte{0x00}, 32);
	const auto key = CreateLegacyLocalKey(passcode, salt);
	const auto ok = key != nullptr && keyIsNonZero(key);
	recordResult(ok, "LegacyLocalKey: CreateLegacyLocalKey -> non-null SHA1-based key");
	assert(ok);
}

int main() {
	testScryptSuccess();
	testScryptFailure();
	testUnknownMarker();
	testRestartUnlock();
	testLegacyUpgrade();
	testMixedState();
	testLegacyLocalKeyCompatibility();

	std::cout << "\n=== KDF TEST RESULT: " << g_passCount << " passed, "
		<< g_failCount << " failed ===\n";
	return g_failCount ? 1 : 0;
}