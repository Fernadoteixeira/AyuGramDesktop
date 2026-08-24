// This is the source code of AyuGram for Desktop.
//
// We do not and cannot prevent the use of our code,
// but be respectful and credit the original author.
//
// Copyright @Radolyn, 2026
#pragma once

#include "ayu/data/entities.h"

#include <QtCore/QString>
#include <QtCore/QByteArray>
#include <vector>

namespace AyuBackup {

inline constexpr auto kBackupMagic = "AYUBACKUP\x01";
inline constexpr auto kMagicSize = 10;
inline constexpr auto kCurrentVersion = 1;
inline constexpr auto kSaltSize = 16;
inline constexpr auto kIvSize = 16;
inline constexpr auto kHmacSize = 32;
inline constexpr auto kPbkdf2Iterations = 100000;

struct Header {
	char magic[kMagicSize];
	uint8_t version = kCurrentVersion;
	uint8_t kdfAlgorithm = 1;
	uint8_t salt[kSaltSize];
	uint8_t iv[kIvSize];
	uint32_t payloadLength = 0;
	uint8_t hmac[kHmacSize];
};

struct ExportOptions {
	bool includeDeletedMessages = true;
	bool includeEditedMessages = true;
	bool includeFilters = true;
	bool includePreferences = true;
	bool includeBadges = true;
};

struct ExportResult {
	bool success = false;
	QString error;
	int64_t bytesWritten = 0;
	int deletedCount = 0;
	int editedCount = 0;
	int filtersCount = 0;
};

struct ImportResult {
	bool success = false;
	QString error;
	int schemaVersion = 0;
	int deletedImported = 0;
	int editedImported = 0;
	int filtersImported = 0;
};

[[nodiscard]] ExportResult ExportToFile(
	const QString &filePath,
	const QString &passcode,
	const ExportOptions &options = ExportOptions());

[[nodiscard]] ImportResult ImportFromFile(
	const QString &filePath,
	const QString &passcode,
	bool overwriteExisting = false);

[[nodiscard]] bool VerifyBackupFile(
	const QString &filePath,
	const QString &passcode,
	QString *outError = nullptr);

} // namespace AyuBackup
