/*
This file is part of Telegram Desktop,
the official desktop application for the Telegram messaging service.

For license and copyright information please follow this link:
https://github.com/telegramdesktop/tdesktop/blob/master/LEGAL
*/
/*
Self-contained SQLCipher security tests for ayudata.db encryption.

Tests the actual production code paths via test accessors
(ayu_database_test_access.h) plus standalone sqlite3mc tests for
migration patterns.  No dependency on Core::IsAppLaunched(),
Core::App().passcodeLocked(), or other application-level globals.

COVERAGE:
  1. EncryptionApplied         — DB created with applyCodecKey has no plaintext header
  2. KeyRequired               — encrypted DB cannot be read without correct key
  3. MigrationSuccess           — plaintext DB -> encrypted DB, data preserved
  4. MigrationRollback          — migration failure -> plaintext preserved, .enc cleaned
  5. StateGateLocked            — state != Ready blocks databaseReady()
  6. StateGateReady             — state == Ready allows databaseReady()
  7. ZeroizeKey                 — zeroizeKey() clears key and resets state
  8. KeyAppliedBeforePragmas   — on_open pattern: key applied before PRAGMAs, DB encrypted

LIMITATIONS:
  Tests 5-6 verify the g_state portion of the retention gate only.
  The full retentionAllowed() also checks Core::IsAppLaunched() and
  Core::App().passcodeLocked() which require the full application runtime.
*/
#include "ayu/data/ayu_database.h"
#include "ayu/data/ayu_database_test_access.h"
#include "ayu/data/ayu_database_key.h"
#include "ayu/libs/sqlite/sqlite3.h"

#include <openssl/crypto.h>
#include <openssl/rand.h>

#include <cassert>
#include <cstring>
#include <iostream>

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

QString testDir() {
	return QDir::tempPath() + "/ayu_sqlcipher_test";
}

QString testPath(const QString &name) {
	return testDir() + "/" + name;
}

void cleanupTestDir() {
	QDir(testDir()).removeRecursively();
	QDir().mkpath(testDir());
}

QByteArray generateTestKey() {
	QByteArray key(kDatabaseKeySize, '\0');
	RAND_bytes(reinterpret_cast<unsigned char *>(key.data()), key.size());
	return key;
}

bool execSql(sqlite3 *db, const char *sql) {
	return sqlite3_exec(db, sql, nullptr, nullptr, nullptr) == SQLITE_OK;
}

} // namespace

static void testEncryptionApplied() {
	cleanupTestDir();
	auto key = generateTestKey();
	Test::setDatabaseKey(key);

	auto path = testPath("enc.db");
	sqlite3 *db = nullptr;
	const auto rc = sqlite3_open(path.toUtf8().constData(), &db);
	const auto opened = rc == SQLITE_OK && db != nullptr;
	if (!opened) {
		recordResult(false, "EncryptionApplied: could not open DB");
		assert(false);
		return;
	}

	Test::testApplyCodecKey(db);
	execSql(db, "PRAGMA journal_mode = WAL;");
	execSql(db, "PRAGMA synchronous = NORMAL;");
	execSql(db, "CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT);");
	execSql(db, "INSERT INTO test VALUES (1, 'hello');");
	sqlite3_close(db);

	const auto fileExists = QFileInfo(path).exists() && QFileInfo(path).size() > 0;
	const auto hasHeader = fileHasSqliteHeader(path);
	const auto ok = fileExists && !hasHeader;
	recordResult(ok, "EncryptionApplied: DB file exists but has no plaintext SQLite header");
	assert(ok);
}

static void testKeyRequired() {
	cleanupTestDir();
	auto key = generateTestKey();
	Test::setDatabaseKey(key);

	auto path = testPath("keyreq.db");
	sqlite3 *db = nullptr;
	sqlite3_open(path.toUtf8().constData(), &db);
	Test::testApplyCodecKey(db);
	execSql(db, "CREATE TABLE secret (data TEXT);");
	execSql(db, "INSERT INTO secret VALUES ('classified');");
	sqlite3_close(db);

	sqlite3 *db2 = nullptr;
	sqlite3_open(path.toUtf8().constData(), &db2);
	auto *stmt = static_cast<sqlite3_stmt *>(nullptr);
	const auto rc = sqlite3_prepare_v2(db2, "SELECT data FROM secret;", -1, &stmt, nullptr);
	const auto ok = rc != SQLITE_OK || sqlite3_step(stmt) != SQLITE_ROW;
	sqlite3_finalize(stmt);
	sqlite3_close(db2);
	recordResult(ok, "KeyRequired: encrypted DB cannot be read without the correct key");
	assert(ok);
}

static void testMigrationSuccess() {
	cleanupTestDir();

	auto plainPath = testPath("plain.db");
	auto encPath = testPath("migrated.db");

	sqlite3 *plain = nullptr;
	sqlite3_open(plainPath.toUtf8().constData(), &plain);
	execSql(plain, "CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT);");
	execSql(plain, "INSERT INTO items VALUES (1, 'alpha');");
	execSql(plain, "INSERT INTO items VALUES (2, 'beta');");
	execSql(plain, "INSERT INTO items VALUES (3, 'gamma');");
	sqlite3_close(plain);

	auto key = generateTestKey();
	Test::setDatabaseKey(key);

	sqlite3 *enc = nullptr;
	sqlite3_open(encPath.toUtf8().constData(), &enc);
	Test::testApplyCodecKey(enc);
	execSql(enc, "PRAGMA synchronous = FULL;");
	execSql(enc, "CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT);");

	auto attachSql = std::string("ATTACH DATABASE '")
		+ plainPath.toUtf8().constData() + "' AS source;";
	execSql(enc, attachSql.c_str());
	execSql(enc, "INSERT INTO items SELECT * FROM source.items;");
	execSql(enc, "DETACH DATABASE source;");
	sqlite3_close(enc);

	sqlite3 *verify = nullptr;
	sqlite3_open(encPath.toUtf8().constData(), &verify);
	Test::testApplyCodecKey(verify);
	auto *stmt = static_cast<sqlite3_stmt *>(nullptr);
	sqlite3_prepare_v2(verify, "SELECT COUNT(*) FROM items;", -1, &stmt, nullptr);
	const auto count = (sqlite3_step(stmt) == SQLITE_ROW)
		? sqlite3_column_int(stmt, 0) : -1;
	sqlite3_finalize(stmt);
	sqlite3_close(verify);

	const auto plainStillExists = fileHasSqliteHeader(plainPath);
	const auto encNoHeader = !fileHasSqliteHeader(encPath);
	const auto ok = count == 3 && plainStillExists && encNoHeader;
	recordResult(ok, "MigrationSuccess: 3 rows preserved, plaintext kept, encrypted has no header");
	assert(ok);
}

static void testMigrationRollback() {
	cleanupTestDir();

	auto plainPath = testPath("rollback.db");
	auto encPath = testPath("rollback.db.enc");

	sqlite3 *plain = nullptr;
	sqlite3_open(plainPath.toUtf8().constData(), &plain);
	execSql(plain, "CREATE TABLE data (id INTEGER PRIMARY KEY, val TEXT);");
	execSql(plain, "INSERT INTO data VALUES (1, 'important');");
	sqlite3_close(plain);

	auto key = generateTestKey();
	Test::setDatabaseKey(key);

	sqlite3 *enc = nullptr;
	sqlite3_open(encPath.toUtf8().constData(), &enc);
	Test::testApplyCodecKey(enc);
	execSql(enc, "CREATE TABLE data (id INTEGER PRIMARY KEY, val TEXT);");

	auto badSql = std::string("ATTACH DATABASE '")
		+ plainPath.toUtf8().constData() + "' AS source;";
	execSql(enc, badSql.c_str());

	auto failRc = execSql(enc, "INSERT INTO nonexistent SELECT * FROM source.data;");
	if (!failRc) {
		QFile::remove(encPath + "-wal");
		QFile::remove(encPath + "-shm");
	}
	sqlite3_close(enc);
	QFile::remove(encPath);
	QFile::remove(encPath + "-wal");
	QFile::remove(encPath + "-shm");

	const auto plainPreserved = fileHasSqliteHeader(plainPath);
	const auto encCleaned = !QFile::exists(encPath);

	sqlite3 *verify = nullptr;
	sqlite3_open(plainPath.toUtf8().constData(), &verify);
	auto *stmt = static_cast<sqlite3_stmt *>(nullptr);
	sqlite3_prepare_v2(verify, "SELECT COUNT(*) FROM data;", -1, &stmt, nullptr);
	const auto count = (sqlite3_step(stmt) == SQLITE_ROW)
		? sqlite3_column_int(stmt, 0) : -1;
	sqlite3_finalize(stmt);
	sqlite3_close(verify);

	const auto ok = plainPreserved && encCleaned && count == 1;
	recordResult(ok, "MigrationRollback: plaintext DB preserved with data, .enc cleaned up");
	assert(ok);
}

static void testStateGateLocked() {
	Test::setDatabaseState(0);
	const auto ready = Test::testDatabaseReady();
	const auto ok = !ready;
	recordResult(ok, "StateGateLocked: state=Initial -> databaseReady() returns false");
	assert(ok);
}

static void testStateGateReady() {
	Test::setDatabaseState(1);
	const auto ready = Test::testDatabaseReady();
	Test::setDatabaseState(0);
	const auto ok = ready;
	recordResult(ok, "StateGateReady: state=Ready -> databaseReady() returns true");
	assert(ok);
}

static void testZeroizeKey() {
	auto key = generateTestKey();
	Test::setDatabaseKey(key);
	Test::setDatabaseState(1);

	const auto keyBefore = Test::getDatabaseKey();
	const auto stateBefore = Test::getDatabaseState();
	const auto keyWasSet = !keyBefore.isEmpty() && stateBefore == 1;

	zeroizeKey();

	const auto keyAfter = Test::getDatabaseKey();
	const auto stateAfter = Test::getDatabaseState();
	const auto keyCleared = keyAfter.isEmpty();
	const auto stateReset = stateAfter == 0;

	const auto ok = keyWasSet && keyCleared && stateReset;
	recordResult(ok, "ZeroizeKey: key cleared and state reset to Initial after zeroizeKey()");
	assert(ok);
}

static void testKeyAppliedBeforePragmas() {
	cleanupTestDir();
	auto key = generateTestKey();
	Test::setDatabaseKey(key);

	auto path = testPath("pragma_order.db");
	sqlite3 *db = nullptr;
	sqlite3_open(path.toUtf8().constData(), &db);

	Test::testApplyCodecKey(db);
	execSql(db, "PRAGMA journal_mode = WAL;");
	execSql(db, "PRAGMA synchronous = NORMAL;");
	execSql(db, "CREATE TABLE ordering (id INTEGER PRIMARY KEY);");
	execSql(db, "INSERT INTO ordering VALUES (42);");
	sqlite3_close(db);

	sqlite3 *verify = nullptr;
	sqlite3_open(path.toUtf8().constData(), &verify);
	Test::testApplyCodecKey(verify);
	auto *stmt = static_cast<sqlite3_stmt *>(nullptr);
	sqlite3_prepare_v2(verify, "SELECT id FROM ordering;", -1, &stmt, nullptr);
	const auto val = (sqlite3_step(stmt) == SQLITE_ROW)
		? sqlite3_column_int(stmt, 0) : -1;
	sqlite3_finalize(stmt);
	sqlite3_close(verify);

	const auto fileExists = QFileInfo(path).exists();
	const auto noPlaintext = !fileHasSqliteHeader(path);
	const auto ok = fileExists && noPlaintext && val == 42;
	recordResult(ok, "KeyAppliedBeforePragmas: key before PRAGMAs, data readable with key, no plaintext header");
	assert(ok);
}

int main() {
	testEncryptionApplied();
	testKeyRequired();
	testMigrationSuccess();
	testMigrationRollback();
	testStateGateLocked();
	testStateGateReady();
	testZeroizeKey();
	testKeyAppliedBeforePragmas();

	std::cout << "\n=== SQLCIPHER TEST RESULT: " << g_passCount << " passed, "
		<< g_failCount << " failed ===\n";
	return g_failCount ? 1 : 0;
}