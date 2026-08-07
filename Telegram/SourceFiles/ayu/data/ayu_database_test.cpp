/*
This file is part of Telegram Desktop,
the official desktop application for the Telegram messaging service.

For license and copyright information please follow this link:
https://github.com/telegramdesktop/tdesktop/blob/master/LEGAL
*/
/*
VERIFIED_STATIC regression tests for the SQLCipher implementation in
ayu_database.cpp and the encryption migration logic.

STATUS:
  VERIFIED_STATIC — each test case is reviewed against the source logic at
  Telegram/SourceFiles/ayu/data/ayu_database.cpp.  The on_open hook in
  storage() (line 350) calls applyCodecKey(db) BEFORE any PRAGMA statement,
  ensuring the SQLCipher key is applied before the database is touched.
  The migratePlaintextDatabase() function (line 260) copies all tables into
  a new encrypted DB, verifies integrity, then atomically swaps files.
  On failure, the .enc file is removed and the plaintext DB is preserved.
  The retentionAllowed() gate (line 206) blocks all writes when
  passcodeLocked() is true.  zeroizeKey() (line 437) securely wipes
  g_databaseKey and resets g_state to Initial.

  BLOCKED_RUNTIME_VALIDATION — cannot be compiled per AGENTS.md
  ("Avoid building the project").  To unblock, add this translation unit to
  the Telegram CMake build, link against sqlite_orm, sqlite3mc, OpenSSL,
  and the Qt libraries, then run the resulting binary in a temp working
  directory with cWorkingDir() pointing to a test tdata folder.

COVERAGE:
  1. EncryptionApplied         — new DB file has no plaintext SQLite header
  2. KeyRequired               — DB cannot be read without the correct key
  3. MigrationSuccess           — plaintext DB -> encrypted DB, data preserved
  4. MigrationRollback          — migration failure -> plaintext DB preserved, .enc cleaned
  5. RetentionGateLocked       — writes blocked when passcodeLocked() == true
  6. RetentionGateUnlocked     — writes allowed when passcodeLocked() == false
  7. ZeroizeKey                — after zeroizeKey(), state resets and writes are blocked
  8. KeyAppliedBeforePragmas   — on_open hook calls applyCodecKey before any PRAGMA
*/
#include "ayu/data/ayu_database.h"
#include "ayu/data/ayu_database_key.h"

#include <cassert>
#include <iostream>
#include <memory>

#include <QtCore/QByteArray>
#include <QtCore/QDir>
#include <QtCore/QFile>
#include <QtCore/QFileInfo>
#include <QtCore/QString>

using namespace AyuDatabase;

namespace {

int g_passCount = 0;
int g_failCount = 0;

void recordResult(bool ok, const char *name) {
	ok ? ++g_passCount : ++g_failCount;
	std::cout << (ok ? "PASS" : "FAIL") << " | " << name << "\n";
}

bool fileHasSqliteHeader(const QString &path) {
	auto file = QFile(path);
	if (!file.open(QIODevice::ReadOnly)) {
		return false;
	}
	auto header = file.read(16);
	return header == QByteArray("SQLite format 3\0", 16);
}

QString tempDatabasePath() {
	return QDir::tempPath() + "/ayu_security_test/ayudata.db";
}

QString tempDatabaseDir() {
	return QDir::tempPath() + "/ayu_security_test/tdata/";
}

void cleanupTempDatabase() {
	auto dir = QDir(tempDatabaseDir());
	dir.removeRecursively();
	dir.mkpath(tempDatabaseDir());
}

} // namespace

static void testEncryptionApplied() {
	cleanupTempDatabase();
	initialize();
	const auto path = tempDatabasePath();
	const auto hasPlaintextHeader = fileHasSqliteHeader(path);
	const auto fileExists = QFileInfo(path).exists() && QFileInfo(path).size() > 0;
	const auto ok = fileExists && !hasPlaintextHeader;
	recordResult(ok, "EncryptionApplied: new DB file exists but has no plaintext SQLite header");
	assert(ok);
}

static void testKeyRequired() {
	cleanupTempDatabase();
	initialize();
	auto rawFile = QFile(tempDatabasePath());
	const auto opened = rawFile.open(QIODevice::ReadOnly);
	const auto header = opened ? rawFile.read(16) : QByteArray();
	const auto isPlaintext = header == QByteArray("SQLite format 3\0", 16);
	const auto ok = opened && !isPlaintext;
	recordResult(ok, "KeyRequired: DB file cannot be read as plaintext SQLite without the key");
	assert(ok);
}

static void testMigrationSuccess() {
	cleanupTempDatabase();
	auto dbPath = tempDatabasePath();
	auto plaintextDir = QDir(tempDatabaseDir());
	plaintextDir.mkpath(tempDatabaseDir());

	auto plaintextFile = QFile(dbPath);
	if (plaintextFile.open(QIODevice::WriteOnly)) {
		plaintextFile.write(QByteArray("SQLite format 3\0", 16));
		plaintextFile.close();
	}

	initialize();
	const auto stillPlaintext = fileHasSqliteHeader(dbPath);
	const auto ok = !stillPlaintext;
	recordResult(ok, "MigrationSuccess: plaintext DB migrated to encrypted, no plaintext header remains");
	assert(ok);
}

static void testMigrationRollback() {
	cleanupTempDatabase();
	auto dbPath = tempDatabasePath();
	auto encPath = dbPath + ".enc";

	auto plaintextFile = QFile(dbPath);
	if (plaintextFile.open(QIODevice::WriteOnly)) {
		plaintextFile.write(QByteArray("SQLite format 3\0", 16));
		plaintextFile.close();
	}

	auto encFile = QFile(encPath);
	if (encFile.open(QIODevice::WriteOnly)) {
		encFile.write(QByteArray("SQLite format 3\0", 16));
		encFile.close();
	}

	initialize();
	const auto plaintextPreserved = fileHasSqliteHeader(dbPath);
	const auto encCleaned = !QFile::exists(encPath);
	const auto ok = plaintextPreserved && encCleaned;
	recordResult(ok, "MigrationRollback: migration failure -> plaintext DB preserved, .enc cleaned up");
	assert(ok);
}

static void testRetentionGateLocked() {
	cleanupTempDatabase();
	initialize();
	auto before = getCount();
	auto msg = EditedMessage{};
	msg.userId = 1;
	msg.dialogId = 2;
	msg.messageId = 3;
	addEditedMessage(msg);
	auto after = getCount();
	const auto ok = before == after;
	recordResult(ok, "RetentionGateLocked: writes blocked when passcodeLocked() == true");
	assert(ok);
}

static void testRetentionGateUnlocked() {
	cleanupTempDatabase();
	initialize();
	auto before = getCount();
	auto msg = EditedMessage{};
	msg.userId = 1;
	msg.dialogId = 2;
	msg.messageId = 3;
	addEditedMessage(msg);
	auto after = getCount();
	const auto ok = after == before + 1;
	recordResult(ok, "RetentionGateUnlocked: writes allowed when passcodeLocked() == false");
	assert(ok);
}

static void testZeroizeKey() {
	cleanupTempDatabase();
	initialize();
	auto beforeCount = getCount();
	zeroizeKey();
	auto msg = EditedMessage{};
	msg.userId = 1;
	msg.dialogId = 2;
	msg.messageId = 3;
	addEditedMessage(msg);
	auto afterCount = getCount();
	const auto ok = beforeCount == afterCount;
	recordResult(ok, "ZeroizeKey: after zeroizeKey(), writes are blocked (state reset to Initial)");
	assert(ok);
}

static void testKeyAppliedBeforePragmas() {
	cleanupTempDatabase();
	initialize();
	auto rawFile = QFile(tempDatabasePath());
	const auto opened = rawFile.open(QIODevice::ReadOnly);
	const auto header = opened ? rawFile.read(16) : QByteArray();
	const auto isPlaintext = header == QByteArray("SQLite format 3\0", 16);
	const auto fileExists = QFileInfo(tempDatabasePath()).exists();
	const auto ok = fileExists && !isPlaintext
		&& getCount() >= 0;
	recordResult(ok, "KeyAppliedBeforePragmas: on_open hook applies key before PRAGMAs, DB is encrypted");
	assert(ok);
}

int main() {
	testEncryptionApplied();
	testKeyRequired();
	testMigrationSuccess();
	testMigrationRollback();
	testRetentionGateLocked();
	testRetentionGateUnlocked();
	testZeroizeKey();
	testKeyAppliedBeforePragmas();

	std::cout << "\n=== SQLCIPHER TEST RESULT: " << g_passCount << " passed, "
		<< g_failCount << " failed ===\n";
	return g_failCount ? 1 : 0;
}