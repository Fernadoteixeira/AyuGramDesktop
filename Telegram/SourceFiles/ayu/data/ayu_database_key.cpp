// This is the source code of AyuGram for Desktop.
//
// We do not and cannot prevent the use of our code,
// but be respectful and credit the original author.
//
// Copyright @Radolyn, 2026
#include "ayu/data/ayu_database_key.h"

#include "base/random.h"
#include "storage/details/storage_file_utilities.h"

#include "settings.h"

#include <QtCore/QString>

namespace AyuDatabase {
namespace {

constexpr auto kKeyFileName = u"ayudata_key"_q;
constexpr qint32 kKeyFileVersion = 1;

[[nodiscard]] QString keyFileBasePath() {
	return cWorkingDir() + u"tdata/"_q;
}

} // namespace

QByteArray generateDatabaseKey() {
	auto key = QByteArray(kDatabaseKeySize, Qt::Uninitialized);
	base::RandomFill(key.data(), key.size());
	return key;
}

bool storeDatabaseKey(const QByteArray &key, const MTP::AuthKeyPtr &localKey) {
	if (key.size() != kDatabaseKeySize || !localKey) {
		LOG(("Database Error: refusing to store invalid DB key."));
		return false;
	}

	using namespace Storage::details;

	auto inner = EncryptedDescriptor(
		uint32(sizeof(qint32) + kDatabaseKeySize));
	inner.stream << kKeyFileVersion;
	inner.stream.writeRawData(key.constData(), key.size());

	{
		auto file = FileWriteDescriptor(kKeyFileName, keyFileBasePath(), true);
		file.writeEncrypted(inner, localKey);
	}

	FileReadDescriptor check;
	if (!ReadFile(check, kKeyFileName, keyFileBasePath())) {
		LOG(("Database Error: could not read back stored DB key file."));
		return false;
	}
	auto encrypted = QByteArray();
	check.stream >> encrypted;
	auto verify = EncryptedDescriptor();
	if (!DecryptLocal(verify, encrypted, localKey)) {
		LOG(("Database Error: stored DB key file failed verification."));
		return false;
	}
	return true;
}

std::optional<QByteArray> loadDatabaseKey(const MTP::AuthKeyPtr &localKey) {
	if (!localKey) {
		return std::nullopt;
	}

	using namespace Storage::details;

	FileReadDescriptor fileData;
	if (!ReadFile(fileData, kKeyFileName, keyFileBasePath())) {
		return std::nullopt;
	}

	auto encrypted = QByteArray();
	fileData.stream >> encrypted;
	if (encrypted.isEmpty()) {
		LOG(("Database Error: DB key file is empty."));
		return std::nullopt;
	}

	auto inner = EncryptedDescriptor();
	if (!DecryptLocal(inner, encrypted, localKey)) {
		LOG(("Database Error: could not unwrap DB key "
			"(passcode reset or corrupted key file)."));
		return std::nullopt;
	}

	auto version = qint32(0);
	inner.stream >> version;
	if (version != kKeyFileVersion) {
		LOG(("Database Error: unsupported DB key file version %1."
			).arg(version));
		return std::nullopt;
	}

	auto key = QByteArray(kDatabaseKeySize, Qt::Uninitialized);
	if (inner.stream.readRawData(key.data(), key.size()) != key.size()) {
		LOG(("Database Error: truncated DB key payload."));
		return std::nullopt;
	}
	return key;
}

}
