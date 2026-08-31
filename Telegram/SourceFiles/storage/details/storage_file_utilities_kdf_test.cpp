/*
This file is part of Telegram Desktop,
the official desktop application for the Telegram messaging service.

For license and copyright information please follow this link:
https://github.com/telegramdesktop/tdesktop/blob/master/LEGAL
*/
#include "storage/details/storage_file_utilities.h"

#include "mtproto/mtproto_auth_key.h"

#include <openssl/evp.h>

#include <cassert>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <vector>

using namespace Storage::details;

namespace {

int g_passCount = 0;
int g_failCount = 0;
bool g_forceScryptFailure = false;

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

class ScopedScryptFailure final {
public:
	ScopedScryptFailure() {
		g_forceScryptFailure = true;
	}

	~ScopedScryptFailure() {
		g_forceScryptFailure = false;
	}
};

} // namespace

extern "C" int __real_EVP_PBE_scrypt(
	const char *pass,
	size_t passlen,
	const unsigned char *salt,
	size_t saltlen,
	uint64_t n,
	uint64_t r,
	uint64_t p,
	uint64_t maxmem,
	unsigned char *key,
	size_t keylen);

extern "C" int __wrap_EVP_PBE_scrypt(
		const char *pass,
		size_t passlen,
		const unsigned char *salt,
		size_t saltlen,
		uint64_t n,
		uint64_t r,
		uint64_t p,
		uint64_t maxmem,
		unsigned char *key,
		size_t keylen) {
	if (g_forceScryptFailure) {
		return 0;
	}
	return __real_EVP_PBE_scrypt(
		pass,
		passlen,
		salt,
		saltlen,
		n,
		r,
		p,
		maxmem,
		key,
		keylen);
}

static void testScryptSuccess() {
	const auto passcode = QByteArray("test-passcode");
	const auto salt = makeSalt(kKdfVersionScrypt, 48);
	const auto key = CreateLocalKey(passcode, salt);
	const auto ok = key != nullptr && keyIsNonZero(key);
	recordResult(ok, "ScryptSuccess: 0x02 marker + non-empty passcode -> valid non-zero key");
	assert(ok);
}

static void testScryptFailure() {
	const auto passcode = QByteArray("forced-scrypt-failure");
	const auto salt = makeSalt(kKdfVersionScrypt, 48);
	auto guard = ScopedScryptFailure();
	const auto key = CreateLocalKey(passcode, salt);
	const auto ok = key == nullptr;
	recordResult(ok, "ScryptFailure: forced EVP_PBE_scrypt failure -> nullptr, no PBKDF2 fallback");
	assert(ok);
}

static void testUnknownMarker() {
	const auto passcode = QByteArray("test-passcode");
	const auto salt = makeSalt(std::byte{0x03}, 48);
	const auto key = CreateLocalKey(passcode, salt);
	const auto ok = key != nullptr && keyIsNonZero(key);
	recordResult(ok, "UnknownMarker: 0x03 marker -> PBKDF2 fallback, non-null key");
	assert(ok);
}

static void testRestartUnlock() {
	const auto passcode = QByteArray("restart-passcode");
	const auto salt = makeSalt(kKdfVersionScrypt, 48);
	const auto key1 = CreateLocalKey(passcode, salt);
	const auto key2 = CreateLocalKey(passcode, salt);
	const auto ok = keysEqual(key1, key2);
	recordResult(ok, "RestartUnlock: same (passcode, salt) -> identical key");
	assert(ok);
}

static void testLegacyUpgrade() {
	const auto passcode = QByteArray("legacy-passcode");
	const auto salt = makeSalt(kKdfVersionPBKDF2, 48);
	const auto key = CreateLocalKey(passcode, salt);
	const auto ok = key != nullptr && keyIsNonZero(key);
	recordResult(ok, "LegacyUpgrade: 0x01 marker -> PBKDF2 path, non-null key");
	assert(ok);
}

static void testMixedState() {
	const auto passcode = QByteArray("mixed-state-passcode");
	const auto scryptSalt = makeSalt(kKdfVersionScrypt, 48);
	auto scryptKey = MTP::AuthKeyPtr();
	{
		auto guard = ScopedScryptFailure();
		scryptKey = CreateLocalKey(passcode, scryptSalt);
	}
	const auto pbkdf2Salt = makeSalt(kKdfVersionPBKDF2, 48);
	const auto pbkdf2Key = CreateLocalKey(passcode, pbkdf2Salt);
	const auto ok = scryptKey == nullptr
		&& pbkdf2Key != nullptr
		&& keyIsNonZero(pbkdf2Key);
	recordResult(ok, "MixedState: forced 0x02 failure -> nullptr while PBKDF2 remains independently valid");
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
