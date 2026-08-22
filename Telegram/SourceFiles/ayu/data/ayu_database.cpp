// This is the source code of AyuGram for Desktop.
//
// We do not and cannot prevent the use of our code,
// but be respectful and credit the original author.
//
// Copyright @Radolyn, 2026
#include "ayu/data/ayu_database.h"

#include "ayu/ayu_settings.h"
#include "ayu/data/ayu_database_key.h"
#include "ayu/data/entities.h"
#include "ayu/libs/sqlite/sqlite_orm.h"
#include "base/unixtime.h"
#include "core/application.h"
#include "main/main_account.h"
#include "main/main_domain.h"
#include "settings.h"
#include "storage/storage_account.h"

#include <openssl/crypto.h>

#include <QtCore/QDir>
#include <QtCore/QFile>

#include <atomic>
#include <limits>
#include <optional>

using namespace sqlite_orm;

QString databaseFilePath() {
	return cWorkingDir() + u"tdata/ayudata.db"_q;
}

auto createStorageForPath(const std::string &path) {
	return make_storage(
		path,
	make_table<SchemaVersion>(
		"SchemaVersion",
		make_column("id", &SchemaVersion::id, primary_key()),
		make_column("version", &SchemaVersion::version)
	),
	make_index("idx_deleted_message_userId_dialogId_topicId_messageId",
			   column<DeletedMessage>(&DeletedMessage::userId),
			   column<DeletedMessage>(&DeletedMessage::dialogId),
			   column<DeletedMessage>(&DeletedMessage::topicId),
			   column<DeletedMessage>(&DeletedMessage::messageId)),
	make_index("idx_deleted_message_userId_dialogId_messageId",
			   column<DeletedMessage>(&DeletedMessage::userId),
			   column<DeletedMessage>(&DeletedMessage::dialogId),
			   column<DeletedMessage>(&DeletedMessage::messageId)),
	make_index("idx_edited_message_userId_dialogId_messageId",
			   column<EditedMessage>(&EditedMessage::userId),
			   column<EditedMessage>(&EditedMessage::dialogId),
			   column<EditedMessage>(&EditedMessage::messageId)),
	make_index("idx_edited_message_userId_dialogId_messageId_fakeId",
			   column<EditedMessage>(&EditedMessage::userId),
			   column<EditedMessage>(&EditedMessage::dialogId),
			   column<EditedMessage>(&EditedMessage::messageId),
			   column<EditedMessage>(&EditedMessage::fakeId)),
	make_index("idx_regex_filter_dialogId",
			   column<RegexFilter>(&RegexFilter::dialogId)),
	make_index("idx_regex_filter_global_exclusion_dialogId",
			   column<RegexFilterGlobalExclusion>(&RegexFilterGlobalExclusion::dialogId)),
	make_index("idx_regex_filter_global_exclusion_filterId",
			   column<RegexFilterGlobalExclusion>(&RegexFilterGlobalExclusion::filterId)),
	make_table<DeletedMessage>(
		"DeletedMessage",
		make_column("fakeId", &DeletedMessage::fakeId, primary_key().autoincrement()),
		make_column("userId", &DeletedMessage::userId),
		make_column("dialogId", &DeletedMessage::dialogId),
		make_column("groupedId", &DeletedMessage::groupedId),
		make_column("peerId", &DeletedMessage::peerId),
		make_column("fromId", &DeletedMessage::fromId),
		make_column("topicId", &DeletedMessage::topicId),
		make_column("messageId", &DeletedMessage::messageId),
		make_column("date", &DeletedMessage::date),
		make_column("flags", &DeletedMessage::flags),
		make_column("editDate", &DeletedMessage::editDate),
		make_column("views", &DeletedMessage::views),
		make_column("fwdFlags", &DeletedMessage::fwdFlags),
		make_column("fwdFromId", &DeletedMessage::fwdFromId),
		make_column("fwdName", &DeletedMessage::fwdName),
		make_column("fwdDate", &DeletedMessage::fwdDate),
		make_column("fwdPostAuthor", &DeletedMessage::fwdPostAuthor),
		make_column("replyFlags", &DeletedMessage::replyFlags),
		make_column("replyMessageId", &DeletedMessage::replyMessageId),
		make_column("replyPeerId", &DeletedMessage::replyPeerId),
		make_column("replyTopId", &DeletedMessage::replyTopId),
		make_column("replyForumTopic", &DeletedMessage::replyForumTopic),
		make_column("replySerialized", &DeletedMessage::replySerialized),
		make_column("entityCreateDate", &DeletedMessage::entityCreateDate),
		make_column("text", &DeletedMessage::text),
		make_column("textEntities", &DeletedMessage::textEntities),
		make_column("mediaPath", &DeletedMessage::mediaPath),
		make_column("hqThumbPath", &DeletedMessage::hqThumbPath),
		make_column("documentType", &DeletedMessage::documentType),
		make_column("documentSerialized", &DeletedMessage::documentSerialized),
		make_column("thumbsSerialized", &DeletedMessage::thumbsSerialized),
		make_column("documentAttributesSerialized", &DeletedMessage::documentAttributesSerialized),
		make_column("mimeType", &DeletedMessage::mimeType)
	),
	make_table<EditedMessage>(
		"EditedMessage",
		make_column("fakeId", &EditedMessage::fakeId, primary_key().autoincrement()),
		make_column("userId", &EditedMessage::userId),
		make_column("dialogId", &EditedMessage::dialogId),
		make_column("groupedId", &EditedMessage::groupedId),
		make_column("peerId", &EditedMessage::peerId),
		make_column("fromId", &EditedMessage::fromId),
		make_column("topicId", &EditedMessage::topicId),
		make_column("messageId", &EditedMessage::messageId),
		make_column("date", &EditedMessage::date),
		make_column("flags", &EditedMessage::flags),
		make_column("editDate", &EditedMessage::editDate),
		make_column("views", &EditedMessage::views),
		make_column("fwdFlags", &EditedMessage::fwdFlags),
		make_column("fwdFromId", &EditedMessage::fwdFromId),
		make_column("fwdName", &EditedMessage::fwdName),
		make_column("fwdDate", &EditedMessage::fwdDate),
		make_column("fwdPostAuthor", &EditedMessage::fwdPostAuthor),
		make_column("replyFlags", &EditedMessage::replyFlags),
		make_column("replyMessageId", &EditedMessage::replyMessageId),
		make_column("replyPeerId", &EditedMessage::replyPeerId),
		make_column("replyTopId", &EditedMessage::replyTopId),
		make_column("replyForumTopic", &EditedMessage::replyForumTopic),
		make_column("replySerialized", &EditedMessage::replySerialized),
		make_column("entityCreateDate", &EditedMessage::entityCreateDate),
		make_column("text", &EditedMessage::text),
		make_column("textEntities", &EditedMessage::textEntities),
		make_column("mediaPath", &EditedMessage::mediaPath),
		make_column("hqThumbPath", &EditedMessage::hqThumbPath),
		make_column("documentType", &EditedMessage::documentType),
		make_column("documentSerialized", &EditedMessage::documentSerialized),
		make_column("thumbsSerialized", &EditedMessage::thumbsSerialized),
		make_column("documentAttributesSerialized", &EditedMessage::documentAttributesSerialized),
		make_column("mimeType", &EditedMessage::mimeType)
	),
	make_table<DeletedDialog>(
		"DeletedDialog",
		make_column("fakeId", &DeletedDialog::fakeId, primary_key().autoincrement()),
		make_column("userId", &DeletedDialog::userId),
		make_column("dialogId", &DeletedDialog::dialogId),
		make_column("peerId", &DeletedDialog::peerId),
		make_column("folderId", &DeletedDialog::folderId),
		make_column("topMessage", &DeletedDialog::topMessage),
		make_column("lastMessageDate", &DeletedDialog::lastMessageDate),
		make_column("flags", &DeletedDialog::flags),
		make_column("entityCreateDate", &DeletedDialog::entityCreateDate)
	),
	make_table<RegexFilter>(
		"RegexFilter",
		make_column("id", &RegexFilter::id, primary_key()),
		make_column("text", &RegexFilter::text),
		make_column("enabled", &RegexFilter::enabled),
		make_column("reversed", &RegexFilter::reversed),
		make_column("caseInsensitive", &RegexFilter::caseInsensitive),
		make_column("dialogId", &RegexFilter::dialogId)
	),
	make_table<RegexFilterGlobalExclusion>(
		"RegexFilterGlobalExclusion",
		make_column("fakeId", &RegexFilterGlobalExclusion::fakeId, primary_key().autoincrement()),
		make_column("dialogId", &RegexFilterGlobalExclusion::dialogId),
		make_column("filterId", &RegexFilterGlobalExclusion::filterId)
	),
	make_table<SpyMessageRead>(
		"SpyMessageRead",
		make_column("fakeId", &SpyMessageRead::fakeId, primary_key().autoincrement()),
		make_column("userId", &SpyMessageRead::userId),
		make_column("dialogId", &SpyMessageRead::dialogId),
		make_column("messageId", &SpyMessageRead::messageId),
		make_column("entityCreateDate", &SpyMessageRead::entityCreateDate)
	),
	make_table<SpyMessageContentsRead>(
		"SpyMessageContentsRead",
		make_column("fakeId", &SpyMessageContentsRead::fakeId, primary_key().autoincrement()),
		make_column("userId", &SpyMessageContentsRead::userId),
		make_column("dialogId", &SpyMessageContentsRead::dialogId),
		make_column("messageId", &SpyMessageContentsRead::messageId),
		make_column("entityCreateDate", &SpyMessageContentsRead::entityCreateDate)
	)
	);
}

auto createStorage() {
	return createStorageForPath(databaseFilePath().toStdString());
}

using Storage = decltype(createStorage());

namespace {

enum class DatabaseState : int {
	Initial,
	Ready,
	Failed,
};

std::atomic<int> g_state = int(DatabaseState::Initial);
QByteArray g_databaseKey;

bool databaseReady() {
	return g_state.load() == int(DatabaseState::Ready);
}

bool retentionAllowed() {
	if (!databaseReady() || !Core::IsAppLaunched()) {
		return false;
	}
	if (!AyuSecurity::canEnableDataRetention()) {
		return false;
	}
	return !Core::App().passcodeLocked();
}

void applyCodecKey(sqlite3 *db) {
	if (g_databaseKey.size() != AyuDatabase::kDatabaseKeySize) {
		LOG(("Database FATAL: opening ayudata.db without a valid key; "
			"all database operations will fail."));
		return;
	}
	sqlite3mc_config(db, "cipher", sqlite3mc_cipher_index("sqlcipher"));
	char spec[4 + AyuDatabase::kDatabaseKeySize];
	memcpy(spec, "raw:", 4);
	memcpy(spec + 4, g_databaseKey.constData(), g_databaseKey.size());
	sqlite3_key(db, spec, sizeof(spec));
	OPENSSL_cleanse(spec, sizeof(spec));
}

[[nodiscard]] bool hasPlaintextHeader(const QString &path) {
	auto file = QFile(path);
	if (!file.open(QIODevice::ReadOnly)) {
		return false;
	}
	return file.read(16) == QByteArray("SQLite format 3\0", 16);
}

MTP::AuthKeyPtr currentLocalKey() {
	if (!Core::IsAppLaunched()) {
		return nullptr;
	}
	auto &domain = Core::App().domain();
	if (!domain.started()) {
		return nullptr;
	}
	return domain.active().local().peekLegacyLocalKey();
}

template <typename T>
void copyTable(Storage &source, Storage &target) {
	const auto rows = source.get_all<T>();
	for (const auto &row : rows) {
		target.replace(row);
	}
	if (int(rows.size()) != target.count<T>()) {
		throw std::runtime_error("row count mismatch during migration");
	}
}

[[nodiscard]] bool migratePlaintextDatabase() {
	const auto path = databaseFilePath();
	if (!hasPlaintextHeader(path)) {
		return false;
	}
	const auto encPath = path + u".enc"_q;

	for (const auto &suffix : { u""_q, u"-wal"_q, u"-shm"_q }) {
		QFile::remove(encPath + suffix);
	}

	try {
		{
			auto source = createStorageForPath(path.toStdString());
			source.pragma.synchronous(2);
			source.pragma.journal_mode(journal_mode::DELETE);
			source.sync_schema(true);

			auto target = createStorageForPath(encPath.toStdString());
			target.on_open = [](sqlite3 *db) {
				applyCodecKey(db);
				sqlite3_exec(db, "PRAGMA synchronous = FULL;", nullptr, nullptr, nullptr);
			};
			target.sync_schema(true);

			target.begin_transaction();
			copyTable<SchemaVersion>(source, target);
			copyTable<DeletedMessage>(source, target);
			copyTable<EditedMessage>(source, target);
			copyTable<DeletedDialog>(source, target);
			copyTable<RegexFilter>(source, target);
			copyTable<RegexFilterGlobalExclusion>(source, target);
			copyTable<SpyMessageRead>(source, target);
			copyTable<SpyMessageContentsRead>(source, target);
			target.commit();

			const auto integrity = target.pragma.integrity_check();
			if (integrity.size() != 1 || integrity.front() != "ok") {
				throw std::runtime_error("integrity check failed");
			}
		}

		const auto backup = cWorkingDir()
			+ u"tdata/ayudata_pre_encryption_%1.db"_q.arg(base::unixtime::now());
		QFile::remove(backup);
		if (!QFile::rename(path, backup)) {
			throw std::runtime_error("could not move plaintext DB aside");
		}
		if (!QFile::rename(encPath, path)) {
			QFile::rename(backup, path);
			throw std::runtime_error("could not replace DB with encrypted copy");
		}
		for (const auto &suffix : { u"-wal"_q, u"-shm"_q }) {
			QFile::remove(path + suffix);
			QFile::remove(backup + suffix);
		}
		LOG(("Database Info: migrated ayudata.db to encrypted storage, "
			"plaintext backup kept at '%1'.").arg(backup));
		return true;
	} catch (const std::exception &ex) {
		LOG(("Database Error: migration to encrypted DB failed: %1"
			).arg(ex.what()));
		for (const auto &suffix : { u""_q, u"-wal"_q, u"-shm"_q }) {
			QFile::remove(encPath + suffix);
		}
		return false;
	}
}

void reportPlaintextArtifacts() {
	const auto dir = QDir(cWorkingDir() + u"tdata"_q);
	const auto entries = dir.entryList(
		{
			u"ayudata_*.db"_q,
			u"ayudata_*.db-wal"_q,
			u"ayudata_*.db-shm"_q,
		},
		QDir::Files);
	for (const auto &entry : entries) {
		LOG(("Database Warning: unencrypted ayudata artifact in tdata: '%1' "
			"(kept for data safety; delete manually if not needed)."
			).arg(entry));
	}
}

} // namespace

namespace AyuMigrations {

void migrateToV1(Storage &db) {
	// drop RegexFilter table as we've added primary_key()
	try {
		db.drop_table_if_exists("RegexFilter");
		LOG(("Migration to V1 successful."));
	} catch (const std::exception &ex) {
		LOG(("Migration to V1 failed: %1").arg(ex.what()));
	}
}

}

void runMigrations(Storage &db) {
	constexpr int kLatestVersion = 1;

	const std::map<int, Fn<void(Storage &)>> migrations = {
		{1, AyuMigrations::migrateToV1},
	};

	int currentVersion = 0;
	try {
		if (auto versionRow = db.get_pointer<SchemaVersion>(1)) {
			currentVersion = versionRow->version;
		} else {
			db.insert(SchemaVersion{1, 0});
		}
	} catch (...) {
		LOG(("No SchemaVersion, assuming 0"));
		db.insert(SchemaVersion{1, 0});
	}

	if (currentVersion >= kLatestVersion) {
		LOG(("Database is ok"));
		return;
	}

	LOG(("Database version: %1. Latest version: %2.").arg(currentVersion).arg(kLatestVersion));

	for (int v = currentVersion + 1; v <= kLatestVersion; ++v) {
		if (migrations.contains(v)) {
			try {
				LOG(("Migration for version: %1").arg(v));
				db.begin_transaction();

				migrations.at(v)(db);

				db.update_all(set(c(&SchemaVersion::version) = v), where(c(&SchemaVersion::id) == 1));
				db.commit();
				LOG(("Applied migration for version: %1.").arg(v));
			} catch (...) {
				db.rollback();
				LOG(("Failed to apply migration for version: %1.").arg(v));
				AyuDatabase::moveCurrentDatabase();

				return;
			}
		}
	}
}

namespace AyuDatabase {

std::optional<Storage> &dbStorageInstance() {
	static std::optional<Storage> instance;
	return instance;
}

Storage &dbStorage() {
	auto &instance = dbStorageInstance();
	if (!instance.has_value()) {
		instance.emplace(createStorage());
		instance->on_open = [](sqlite3 *db) {
			applyCodecKey(db);
			sqlite3_exec(db, "PRAGMA journal_mode = WAL;", nullptr, nullptr, nullptr);
			sqlite3_exec(db, "PRAGMA synchronous = NORMAL;", nullptr, nullptr, nullptr);
		};
	}
	return *instance;
}

void moveCurrentDatabase() {
	const auto time = base::unixtime::now();
	const auto path = databaseFilePath();

	for (const auto &suffix : { u""_q, u"-shm"_q, u"-wal"_q }) {
		const auto current = path + suffix;
		if (QFile::exists(current)) {
			const auto renamed = cWorkingDir() + u"tdata/ayudata_%1.db"_q.arg(time) + suffix;
			QFile::rename(current, renamed);
		}
	}
}

void zeroizeKey() {
	if (!g_databaseKey.isEmpty()) {
		OPENSSL_cleanse(g_databaseKey.data(), g_databaseKey.size());
		g_databaseKey.clear();
		g_databaseKey.squeeze();
	}
	dbStorageInstance().reset();
	g_state = int(DatabaseState::Initial);
}

void initialize() {
	auto expected = int(DatabaseState::Initial);
	if (!g_state.compare_exchange_strong(expected, int(DatabaseState::Failed))) {
		return;
	}

	const auto localKey = currentLocalKey();
	if (!localKey) {
		LOG(("Database Info: domain is not unlocked yet, "
			"deferring ayudata.db initialization."));
		g_state = int(DatabaseState::Initial);
		return;
	}

	const auto path = databaseFilePath();
	const auto exists = QFile::exists(path) && QFileInfo(path).size() > 0;
	const auto plaintext = exists && hasPlaintextHeader(path);

	auto key = loadDatabaseKey(localKey);
	if (!key) {
		if (!exists || plaintext) {
			key = generateDatabaseKey();
		} else {
			LOG(("Database Error: encrypted ayudata.db exists but its key "
				"could not be unwrapped (passcode reset?). "
				"Moving the DB aside and starting fresh."));
			moveCurrentDatabase();
			key = generateDatabaseKey();
		}
		if (!storeDatabaseKey(*key, localKey)) {
			LOG(("Database Error: could not persist the DB key, "
				"retention is disabled for this session."));
			return;
		}
	}

	g_databaseKey = *key;

	if (plaintext) {
		if (!migratePlaintextDatabase()) {
			if (!g_databaseKey.isEmpty()) {
				OPENSSL_cleanse(g_databaseKey.data(), g_databaseKey.size());
			}
			g_databaseKey.clear();
			g_databaseKey.squeeze();
			return;
		}
	}

	try {
		dbStorage().sync_schema(true);

		runMigrations(dbStorage());

		dbStorage().sync_schema(true);
	} catch (const std::exception &ex) {
		LOG(("Database initialization failed: %1").arg(ex.what()));
		moveCurrentDatabase();

		try {
			dbStorage().sync_schema(true);
			if (!dbStorage().get_pointer<SchemaVersion>(1)) {
				dbStorage().insert(SchemaVersion{1, 0});
			}
		} catch (const std::exception &ex2) {
			LOG(("Database Error: could not recover ayudata.db: %1, "
				"retention is disabled for this session."
				).arg(ex2.what()));
			if (!g_databaseKey.isEmpty()) {
				OPENSSL_cleanse(g_databaseKey.data(), g_databaseKey.size());
			}
			g_databaseKey.clear();
			g_databaseKey.squeeze();
			return;
		}
	}

	reportPlaintextArtifacts();
	g_state = int(DatabaseState::Ready);
}

void addEditedMessage(const EditedMessage &message) {
	if (!retentionAllowed()) {
		return;
	}
	try {
		dbStorage().begin_transaction();
		dbStorage().insert(message);
		dbStorage().commit();
	} catch (std::exception &ex) {
		try {
			dbStorage().rollback();
		} catch (...) {
		}
		LOG(("Failed to save edited message for some reason: %1").arg(ex.what()));
	}
}

std::vector<EditedMessage> getEditedMessages(ID userId, ID dialogId, ID messageId, ID minId, ID maxId, int totalLimit) {
	if (!retentionAllowed()) {
		return {};
	}
	const auto lowerFakeId = (minId == 0) ? std::numeric_limits<ID>::lowest() : minId;
	const auto upperFakeId = (maxId == 0) ? std::numeric_limits<ID>::max() : maxId;
	return dbStorage().get_all<EditedMessage>(
		where(
			column<EditedMessage>(&EditedMessage::userId) == userId and
			column<EditedMessage>(&EditedMessage::dialogId) == dialogId and
			column<EditedMessage>(&EditedMessage::messageId) == messageId and
			column<EditedMessage>(&EditedMessage::fakeId) > lowerFakeId and
			column<EditedMessage>(&EditedMessage::fakeId) < upperFakeId
		),
		order_by(column<EditedMessage>(&EditedMessage::fakeId)).desc(),
		limit(totalLimit)
	);
}

bool hasRevisions(ID userId, ID dialogId, ID messageId) {
	if (!retentionAllowed()) {
		return false;
	}
	try {
		return !dbStorage().select(
			columns(column<EditedMessage>(&EditedMessage::messageId)),
			where(
				column<EditedMessage>(&EditedMessage::userId) == userId and
				column<EditedMessage>(&EditedMessage::dialogId) == dialogId and
				column<EditedMessage>(&EditedMessage::messageId) == messageId
			),
			limit(1)
		).empty();
	} catch (std::exception &ex) {
		LOG(("Failed to check if message has revisions: %1").arg(ex.what()));
		return false;
	}
}

void addDeletedMessage(const DeletedMessage &message) {
	if (!retentionAllowed()) {
		return;
	}
	try {
		dbStorage().begin_transaction();
		dbStorage().insert(message);
		dbStorage().commit();
	} catch (std::exception &ex) {
		try {
			dbStorage().rollback();
		} catch (...) {
		}
		LOG(("Failed to save edited message for some reason: %1").arg(ex.what()));
	}
}

std::vector<DeletedMessage> getDeletedMessages(ID userId, ID dialogId, ID topicId, ID minId, ID maxId, int totalLimit, const std::string &searchQuery) {
	if (!retentionAllowed()) {
		return {};
	}
	const auto lowerMessageId = (minId == 0) ? std::numeric_limits<ID>::lowest() : minId;
	const auto upperMessageId = (maxId == 0) ? std::numeric_limits<ID>::max() : maxId;
	if (searchQuery.empty()) {
		if (topicId == 0) {
			return dbStorage().get_all<DeletedMessage>(
				where(
					column<DeletedMessage>(&DeletedMessage::userId) == userId and
					column<DeletedMessage>(&DeletedMessage::dialogId) == dialogId and
					column<DeletedMessage>(&DeletedMessage::messageId) > lowerMessageId and
					column<DeletedMessage>(&DeletedMessage::messageId) < upperMessageId
				),
				order_by(column<DeletedMessage>(&DeletedMessage::messageId)).desc(),
				limit(totalLimit)
			);
		}
		return dbStorage().get_all<DeletedMessage>(
			where(
				column<DeletedMessage>(&DeletedMessage::userId) == userId and
				column<DeletedMessage>(&DeletedMessage::dialogId) == dialogId and
				column<DeletedMessage>(&DeletedMessage::topicId) == topicId and
				column<DeletedMessage>(&DeletedMessage::messageId) > lowerMessageId and
				column<DeletedMessage>(&DeletedMessage::messageId) < upperMessageId
			),
			order_by(column<DeletedMessage>(&DeletedMessage::messageId)).desc(),
			limit(totalLimit)
		);
	}

	std::string escaped;
	escaped.reserve(searchQuery.size());
	for (const auto c : searchQuery) {
		if (c == '%' || c == '_' || c == '\\') {
			escaped += '\\';
		}
		escaped += c;
	}
	const auto pattern = "%" + escaped + "%";
	if (topicId == 0) {
		return dbStorage().get_all<DeletedMessage>(
			where(
				column<DeletedMessage>(&DeletedMessage::userId) == userId and
				column<DeletedMessage>(&DeletedMessage::dialogId) == dialogId and
				column<DeletedMessage>(&DeletedMessage::messageId) > lowerMessageId and
				column<DeletedMessage>(&DeletedMessage::messageId) < upperMessageId and
				like(column<DeletedMessage>(&DeletedMessage::text), pattern, "\\")
			),
			order_by(column<DeletedMessage>(&DeletedMessage::messageId)).desc(),
			limit(totalLimit)
		);
	}
	return dbStorage().get_all<DeletedMessage>(
		where(
			column<DeletedMessage>(&DeletedMessage::userId) == userId and
			column<DeletedMessage>(&DeletedMessage::dialogId) == dialogId and
			column<DeletedMessage>(&DeletedMessage::topicId) == topicId and
			column<DeletedMessage>(&DeletedMessage::messageId) > lowerMessageId and
			column<DeletedMessage>(&DeletedMessage::messageId) < upperMessageId and
			like(column<DeletedMessage>(&DeletedMessage::text), pattern, "\\")
		),
		order_by(column<DeletedMessage>(&DeletedMessage::messageId)).desc(),
		limit(totalLimit)
	);
}

bool hasDeletedMessages(ID userId, ID dialogId, ID topicId) {
	if (!retentionAllowed()) {
		return false;
	}
	try {
		if (topicId == 0) {
			return !dbStorage().select(
				columns(column<DeletedMessage>(&DeletedMessage::dialogId)),
				where(
					column<DeletedMessage>(&DeletedMessage::userId) == userId and
					column<DeletedMessage>(&DeletedMessage::dialogId) == dialogId
				),
				limit(1)
			).empty();
		}
		return !dbStorage().select(
			columns(column<DeletedMessage>(&DeletedMessage::dialogId)),
			where(
				column<DeletedMessage>(&DeletedMessage::userId) == userId and
				column<DeletedMessage>(&DeletedMessage::dialogId) == dialogId and
				column<DeletedMessage>(&DeletedMessage::topicId) == topicId
			),
			limit(1)
		).empty();
	} catch (std::exception &ex) {
		LOG(("Failed to check if dialog has deleted message: %1").arg(ex.what()));
		return false;
	}
}

void clearDeletedMessages(ID userId, ID dialogId, ID topicId) {
	if (!retentionAllowed()) {
		return;
	}
	try {
		if (topicId == 0) {
			dbStorage().template remove_all<DeletedMessage>(
				where(
					column<DeletedMessage>(&DeletedMessage::userId) == userId and
					column<DeletedMessage>(&DeletedMessage::dialogId) == dialogId
				)
			);
			return;
		}
		dbStorage().template remove_all<DeletedMessage>(
			where(
				column<DeletedMessage>(&DeletedMessage::userId) == userId and
				column<DeletedMessage>(&DeletedMessage::dialogId) == dialogId and
				column<DeletedMessage>(&DeletedMessage::topicId) == topicId
			)
		);
	} catch (std::exception &) {
	}
}

template<typename T>
std::vector<T> getAllT() {
	try {
		return dbStorage().template get_all<T>();
	} catch (std::exception &ex) {
		LOG(("Failed to get all: %1").arg(ex.what()));
		return {};
	}
}

std::vector<RegexFilter> getAllRegexFilters() {
	if (!retentionAllowed()) {
		return {};
	}
	return getAllT<RegexFilter>();
}

std::vector<RegexFilterGlobalExclusion> getAllFiltersExclusions() {
	if (!retentionAllowed()) {
		return {};
	}
	return getAllT<RegexFilterGlobalExclusion>();
}

std::vector<RegexFilter> getExcludedByDialogId(ID dialogId) {
	if (!retentionAllowed()) {
		return {};
	}
	try {
		return dbStorage().template get_all<RegexFilter>(
			where(in(&RegexFilter::id,
					 dbStorage().select(columns(&RegexFilterGlobalExclusion::filterId),
									where(is_equal(&RegexFilterGlobalExclusion::dialogId, dialogId))
					 )
			))
		);
	} catch (std::exception &ex) {
		LOG(("Failed to get excluded by dialog id: %1").arg(ex.what()));
		return {};
	}
}

int getCount() {
	if (!retentionAllowed()) {
		return 0;
	}
	try {
		return dbStorage().template count<RegexFilter>();
	} catch (std::exception &ex) {
		LOG(("Failed to get count: %1").arg(ex.what()));
		return 0;
	}
}

RegexFilter getById(std::vector<char> id) {
	if (!retentionAllowed()) {
		return {};
	}
	try {
		return dbStorage().template get<RegexFilter>(
			where(column<RegexFilter>(&RegexFilter::id) == std::move(id))
		);
	} catch (std::exception &ex) {
		LOG(("Failed to get filters by id: %1").arg(ex.what()));
		return {};
	}
}

std::vector<RegexFilter> getShared() {
	if (!retentionAllowed()) {
		return {};
	}
	try {
		return dbStorage().template get_all<RegexFilter>(
			where(is_null(column<RegexFilter>(&RegexFilter::dialogId)))
		);
	} catch (std::exception &ex) {
		LOG(("Failed to get shared filters: %1").arg(ex.what()));
		return {};
	}
}

std::vector<RegexFilter> getByDialogId(ID dialogId) {
	if (!retentionAllowed()) {
		return {};
	}
	try {
		return dbStorage().template get_all<RegexFilter>(
			where(column<RegexFilter>(&RegexFilter::dialogId) == dialogId)
		);
	} catch (std::exception &ex) {
		LOG(("Failed to get filters by dialog id: %1").arg(ex.what()));
		return {};
	}
}

void addRegexFilter(const RegexFilter &filter) {
	if (!retentionAllowed()) {
		return;
	}
	try {
		dbStorage().begin_transaction();
		dbStorage().replace(filter); // we're using replace as we set std::vector<char> as primary key
		dbStorage().commit();
	} catch (std::exception &ex) {
		try {
			dbStorage().rollback();
		} catch (...) {
		}
		LOG(("Failed to save regex filter for some reason: %1").arg(ex.what()));
	}
}

void addRegexExclusion(const RegexFilterGlobalExclusion &exclusion) {
	if (!retentionAllowed()) {
		return;
	}
	try {
		dbStorage().begin_transaction();
		dbStorage().insert(exclusion);
		dbStorage().commit();
	} catch (std::exception &ex) {
		try {
			dbStorage().rollback();
		} catch (...) {
		}
		LOG(("Failed to save regex filter exclusion for some reason: %1").arg(ex.what()));
	}
}

void updateRegexFilter(const RegexFilter &filter) {
	if (!retentionAllowed()) {
		return;
	}
	try {
		dbStorage().update_all(
			set(
				c(&RegexFilter::text) = filter.text,
				c(&RegexFilter::enabled) = filter.enabled,
				c(&RegexFilter::reversed) = filter.reversed,
				c(&RegexFilter::caseInsensitive) = filter.caseInsensitive,
				c(&RegexFilter::dialogId) = filter.dialogId
			),
			where(c(&RegexFilter::id) == filter.id)
		);
	} catch (std::exception &ex) {
		LOG(("Failed to update regex filter for some reason: %1").arg(ex.what()));
	}
}

void deleteFilter(const std::vector<char> &id) {
	if (!retentionAllowed()) {
		return;
	}
	try {
		dbStorage().template remove_all<RegexFilter>(
			where(column<RegexFilter>(&RegexFilter::id) == id)
		);
	} catch (std::exception &ex) {
		LOG(("Failed to delete regex filter for some reason: %1").arg(ex.what()));
	}
}

void deleteExclusionsByFilterId(const std::vector<char> &id) {
	if (!retentionAllowed()) {
		return;
	}
	try {
		dbStorage().template remove_all<RegexFilterGlobalExclusion>(
			where(column<RegexFilterGlobalExclusion>(&RegexFilterGlobalExclusion::filterId) == id)
		);
	} catch (std::exception &ex) {
		LOG(("Failed to delete regex filter exclusion by filter id for some reason: %1").arg(ex.what()));
	}
}

void deleteExclusion(ID dialogId, std::vector<char> filterId) {
	if (!retentionAllowed()) {
		return;
	}
	try {
		dbStorage().template remove_all<RegexFilterGlobalExclusion>(
			where(column<RegexFilterGlobalExclusion>(&RegexFilterGlobalExclusion::filterId) == filterId and
				column<RegexFilterGlobalExclusion>(&RegexFilterGlobalExclusion::dialogId) == dialogId
			)
		);
	} catch (std::exception &ex) {
		LOG(("Failed to delete regex filter exclusion for some reason: %1").arg(ex.what()));
	}
}

void deleteAllFilters() {
	if (!retentionAllowed()) {
		return;
	}
	try {
		dbStorage().template remove_all<RegexFilter>();
	} catch (std::exception &ex) {
		LOG(("Failed to delete all regex filter for some reason: %1").arg(ex.what()));
	}
}

void deleteAllExclusions() {
	if (!retentionAllowed()) {
		return;
	}
	try {
		dbStorage().template remove_all<RegexFilterGlobalExclusion>();
	} catch (std::exception &ex) {
		LOG(("Failed to delete all regex filter exclusions for some reason: %1").arg(ex.what()));
	}
}

bool hasFilters() {
	if (!retentionAllowed()) {
		return false;
	}
	try {
		return !dbStorage().select(
			columns(column<RegexFilter>(&RegexFilter::id)),
			limit(1)
		).empty();
	} catch (std::exception &ex) {
		LOG(("Failed to check if there's any filters: %1").arg(ex.what()));
		return false;
	}
}

bool hasPerDialogFilters() {
	if (!retentionAllowed()) {
		return false;
	}
	try {
		return
			!dbStorage().select(
				columns(column<RegexFilter>(&RegexFilter::id)),
				where(is_not_null(column<RegexFilter>(&RegexFilter::dialogId))),
				limit(1)
			).empty() ||
			!dbStorage().select(
				columns(column<RegexFilterGlobalExclusion>(&RegexFilterGlobalExclusion::fakeId)),
				limit(1)
			).empty();
	} catch (std::exception &ex) {
		LOG(("Failed to check if there's any filters: %1").arg(ex.what()));
		return false;
	}
}

namespace Test {

QByteArray getDatabaseKey() {
	return g_databaseKey;
}

void setDatabaseKey(const QByteArray &key) {
	g_databaseKey = key;
}

int getDatabaseState() {
	return g_state.load();
}

void setDatabaseState(int state) {
	g_state = state;
}

bool testDatabaseReady() {
	return databaseReady();
}

bool testHasPlaintextHeader(const QString &path) {
	return hasPlaintextHeader(path);
}

void testApplyCodecKey(sqlite3 *db) {
	applyCodecKey(db);
}

} // namespace Test

}
