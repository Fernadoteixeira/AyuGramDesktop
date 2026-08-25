// This is the source code of AyuGram for Desktop.
//
// We do not and cannot prevent the use of our code,
// but be respectful and credit the original author.
//
// Copyright @Radolyn, 2026
#include "ayu/data/ayu_backup.h"

#include "ayu/data/ayu_database.h"
#include "ayu/ayu_settings.h"
#include "base/random.h"
#include "settings.h"

#include <QtCore/QByteArray>
#include <QtCore/QString>
#include <QtCore/QDateTime>
#include <QtCore/QFile>
#include <QtCore/QSaveFile>
#include <QtCore/QJsonDocument>
#include <QtCore/QJsonObject>
#include <QtCore/QJsonArray>

#include <openssl/evp.h>
#include <openssl/hmac.h>
#include <openssl/crypto.h>

namespace AyuBackup {
namespace {

constexpr auto kDerivedKeySize = 64;
constexpr auto kAesKeySize = 32;
constexpr auto kPbkdf2Iterations = 100000;

struct DerivedKeys {
	uint8_t aesKey[kAesKeySize];
	uint8_t hmacKey[kAesKeySize];
};

[[nodiscard]] bool DeriveKeys(
		const QString &passcode,
		const uint8_t *salt,
		int saltLen,
		DerivedKeys *outKeys) {
	const auto utf8 = passcode.toUtf8();
	uint8_t raw[kDerivedKeySize] = { 0 };

	const auto ok = PKCS5_PBKDF2_HMAC(
		utf8.constData(),
		utf8.size(),
		salt,
		saltLen,
		kPbkdf2Iterations,
		EVP_sha256(),
		kDerivedKeySize,
		raw);

	if (ok == 1) {
		memcpy(outKeys->aesKey, raw, kAesKeySize);
		memcpy(outKeys->hmacKey, raw + kAesKeySize, kAesKeySize);
		OPENSSL_cleanse(raw, sizeof(raw));
		return true;
	}

	OPENSSL_cleanse(raw, sizeof(raw));
	return false;
}

[[nodiscard]] QByteArray ComputeHmac(
		const uint8_t *key,
		int keyLen,
		const uint8_t *data,
		size_t dataLen) {
	unsigned int len = kHmacSize;
	uint8_t digest[EVP_MAX_MD_SIZE] = { 0 };

	const auto res = HMAC(
		EVP_sha256(),
		key,
		keyLen,
		data,
		dataLen,
		digest,
		&len);

	if (!res || len != kHmacSize) {
		return QByteArray();
	}
	return QByteArray(reinterpret_cast<const char*>(digest), kHmacSize);
}

[[nodiscard]] QByteArray EncryptAes256(
		const QByteArray &plain,
		const uint8_t *key,
		const uint8_t *iv) {
	auto ctx = EVP_CIPHER_CTX_new();
	if (!ctx) {
		return QByteArray();
	}

	auto cipher = QByteArray(plain.size() + EVP_MAX_BLOCK_LENGTH, Qt::Uninitialized);
	auto outLen1 = 0;
	auto outLen2 = 0;

	if (EVP_EncryptInit_ex(ctx, EVP_aes_256_cbc(), nullptr, key, iv) != 1
		|| EVP_EncryptUpdate(ctx, reinterpret_cast<uint8_t*>(cipher.data()), &outLen1, reinterpret_cast<const uint8_t*>(plain.constData()), plain.size()) != 1
		|| EVP_EncryptFinal_ex(ctx, reinterpret_cast<uint8_t*>(cipher.data()) + outLen1, &outLen2) != 1) {
		EVP_CIPHER_CTX_free(ctx);
		return QByteArray();
	}

	EVP_CIPHER_CTX_free(ctx);
	cipher.resize(outLen1 + outLen2);
	return cipher;
}

[[nodiscard]] QByteArray DecryptAes256(
		const QByteArray &cipher,
		const uint8_t *key,
		const uint8_t *iv) {
	auto ctx = EVP_CIPHER_CTX_new();
	if (!ctx) {
		return QByteArray();
	}

	auto plain = QByteArray(cipher.size() + EVP_MAX_BLOCK_LENGTH, Qt::Uninitialized);
	auto outLen1 = 0;
	auto outLen2 = 0;

	if (EVP_DecryptInit_ex(ctx, EVP_aes_256_cbc(), nullptr, key, iv) != 1
		|| EVP_DecryptUpdate(ctx, reinterpret_cast<uint8_t*>(plain.data()), &outLen1, reinterpret_cast<const uint8_t*>(cipher.constData()), cipher.size()) != 1
		|| EVP_DecryptFinal_ex(ctx, reinterpret_cast<uint8_t*>(plain.data()) + outLen1, &outLen2) != 1) {
		EVP_CIPHER_CTX_free(ctx);
		return QByteArray();
	}

	EVP_CIPHER_CTX_free(ctx);
	plain.resize(outLen1 + outLen2);
	return plain;
}

} // namespace

ExportResult ExportToFile(
		const QString &filePath,
		const QString &passcode,
		const ExportOptions &options) {
	auto result = ExportResult();
	if (passcode.isEmpty()) {
		result.error = u"Passcode cannot be empty."_q;
		return result;
	}

	auto root = QJsonObject();
	root[u"version"_q] = kCurrentVersion;
	root[u"timestamp"_q] = double(QDateTime::currentSecsSinceEpoch());

	if (options.includePreferences) {
		auto settingsObj = QJsonObject();
		settingsObj[u"sendReadMessages"_q] = AyuSettings::sendReadMessages();
		settingsObj[u"sendReadStories"_q] = AyuSettings::sendReadStories();
		settingsObj[u"sendOnlinePackets"_q] = AyuSettings::sendOnlinePackets();
		settingsObj[u"sendUploadProgress"_q] = AyuSettings::sendUploadProgress();
		settingsObj[u"sendOfflinePacketAfterOnline"_q] = AyuSettings::sendOfflinePacketAfterOnline();
		settingsObj[u"saveDeletedMessages"_q] = AyuSettings::saveDeletedMessages();
		settingsObj[u"saveEditedMessages"_q] = AyuSettings::saveEditedMessages();
		settingsObj[u"streamerMode"_q] = AyuSettings::streamerMode();
		root[u"settings"_q] = settingsObj;
	}

	if (options.includeFilters) {
		auto filtersArray = QJsonArray();
		const auto allFilters = AyuDatabase::getAllRegexFilters();
		for (const auto &filter : allFilters) {
			auto obj = QJsonObject();
			const auto idBytes = QByteArray(filter.id.data(), filter.id.size());
			obj[u"id"_q] = QString::fromUtf8(idBytes.toHex());
			obj[u"text"_q] = QString::fromStdString(filter.text);
			obj[u"enabled"_q] = bool(filter.enabled);
			obj[u"reversed"_q] = bool(filter.reversed);
			obj[u"caseInsensitive"_q] = bool(filter.caseInsensitive);
			if (filter.dialogId) {
				obj[u"dialogId"_q] = double(*filter.dialogId);
			}
			filtersArray.append(obj);
		}
		root[u"filters"_q] = filtersArray;
		result.filtersCount = int(allFilters.size());
	}

	const auto doc = QJsonDocument(root);
	const auto plain = doc.toJson(QJsonDocument::Compact);

	Header header;
	memcpy(header.magic, kBackupMagic, kMagicSize);
	header.version = kCurrentVersion;
	header.kdfAlgorithm = 1;
	base::RandomFill(header.salt, kSaltSize);
	base::RandomFill(header.iv, kIvSize);

	DerivedKeys keys;
	if (!DeriveKeys(passcode, header.salt, kSaltSize, &keys)) {
		result.error = u"Failed to derive cryptographic key."_q;
		return result;
	}

	const auto cipher = EncryptAes256(plain, keys.aesKey, header.iv);
	if (cipher.isEmpty()) {
		OPENSSL_cleanse(&keys, sizeof(keys));
		result.error = u"Payload encryption failed."_q;
		return result;
	}

	header.payloadLength = uint32_t(cipher.size());

	auto hmacTarget = QByteArray();
	hmacTarget.append(reinterpret_cast<const char*>(&header), offsetof(Header, hmac));
	hmacTarget.append(cipher);

	const auto hmac = ComputeHmac(
		keys.hmacKey,
		kAesKeySize,
		reinterpret_cast<const uint8_t*>(hmacTarget.constData()),
		hmacTarget.size());
	OPENSSL_cleanse(&keys, sizeof(keys));

	if (hmac.size() != kHmacSize) {
		result.error = u"HMAC signature generation failed."_q;
		return result;
	}
	memcpy(header.hmac, hmac.constData(), kHmacSize);

	auto save = QSaveFile(filePath);
	if (!save.open(QIODevice::WriteOnly)) {
		result.error = u"Could not open file for writing: "_q + filePath;
		return result;
	}

	save.write(reinterpret_cast<const char*>(&header), sizeof(Header));
	save.write(cipher);

	if (!save.commit()) {
		result.error = u"Could not commit backup file write."_q;
		return result;
	}

	result.success = true;
	result.bytesWritten = int64_t(sizeof(Header) + cipher.size());
	return result;
}

ImportResult ImportFromFile(
		const QString &filePath,
		const QString &passcode,
		bool overwriteExisting) {
	auto result = ImportResult();
	auto file = QFile(filePath);
	if (!file.open(QIODevice::ReadOnly)) {
		result.error = u"Cannot open backup file: "_q + filePath;
		return result;
	}

	if (file.size() < qint64(sizeof(Header))) {
		result.error = u"Corrupted backup header: file too small."_q;
		return result;
	}

	Header header;
	if (file.read(reinterpret_cast<char*>(&header), sizeof(Header)) != sizeof(Header)) {
		result.error = u"Failed to read backup header."_q;
		return result;
	}

	if (memcmp(header.magic, kBackupMagic, kMagicSize) != 0) {
		result.error = u"Invalid backup magic signature."_q;
		return result;
	}

	if (header.version != kCurrentVersion) {
		result.error = u"Unsupported backup container version."_q;
		return result;
	}

	const auto cipher = file.read(header.payloadLength);
	if (cipher.size() != int(header.payloadLength)) {
		result.error = u"Truncated backup payload."_q;
		return result;
	}

	DerivedKeys keys;
	if (!DeriveKeys(passcode, header.salt, kSaltSize, &keys)) {
		result.error = u"Key derivation failed."_q;
		return result;
	}

	auto hmacTarget = QByteArray();
	hmacTarget.append(reinterpret_cast<const char*>(&header), offsetof(Header, hmac));
	hmacTarget.append(cipher);

	const auto computedHmac = ComputeHmac(
		keys.hmacKey,
		kAesKeySize,
		reinterpret_cast<const uint8_t*>(hmacTarget.constData()),
		hmacTarget.size());

	if (computedHmac.size() != kHmacSize
		|| CRYPTO_memcmp(computedHmac.constData(), header.hmac, kHmacSize) != 0) {
		OPENSSL_cleanse(&keys, sizeof(keys));
		result.error = u"Invalid passcode or corrupted/tampered backup file."_q;
		return result;
	}

	const auto plain = DecryptAes256(cipher, keys.aesKey, header.iv);
	OPENSSL_cleanse(&keys, sizeof(keys));

	if (plain.isEmpty()) {
		result.error = u"Decryption failed."_q;
		return result;
	}

	auto parseError = QJsonParseError();
	const auto doc = QJsonDocument::fromJson(plain, &parseError);
	if (parseError.error != QJsonParseError::NoError || !doc.isObject()) {
		result.error = u"Invalid payload structure: "_q + parseError.errorString();
		return result;
	}

	const auto root = doc.object();
	result.schemaVersion = root.value(u"version"_q).toInt(1);

	if (root.contains(u"filters"_q) && root.value(u"filters"_q).isArray()) {
		const auto array = root.value(u"filters"_q).toArray();
		for (const auto &val : array) {
			if (!val.isObject()) {
				continue;
			}
			const auto obj = val.toObject();
			const auto idHex = obj.value(u"id"_q).toString();
			const auto idBytes = QByteArray::fromHex(idHex.toUtf8());
			if (idBytes.isEmpty()) {
				continue;
			}

			RegexFilter filter;
			filter.id = std::vector<char>(idBytes.constData(), idBytes.constData() + idBytes.size());
			filter.text = obj.value(u"text"_q).toString().toStdString();
			filter.enabled = obj.value(u"enabled"_q).toBool() ? 1 : 0;
			filter.reversed = obj.value(u"reversed"_q).toBool() ? 1 : 0;
			filter.caseInsensitive = obj.value(u"caseInsensitive"_q).toBool() ? 1 : 0;
			if (obj.contains(u"dialogId"_q)) {
				filter.dialogId = ID(obj.value(u"dialogId"_q).toDouble());
			}

			if (overwriteExisting) {
				AyuDatabase::updateRegexFilter(filter);
			} else {
				AyuDatabase::addRegexFilter(filter);
			}
			result.filtersImported++;
		}
	}

	result.success = true;
	return result;
}

bool VerifyBackupFile(
		const QString &filePath,
		const QString &passcode,
		QString *outError) {
	auto file = QFile(filePath);
	if (!file.open(QIODevice::ReadOnly)) {
		if (outError) *outError = u"Cannot open file."_q;
		return false;
	}

	if (file.size() < qint64(sizeof(Header))) {
		if (outError) *outError = u"File is too small."_q;
		return false;
	}

	Header header;
	if (file.read(reinterpret_cast<char*>(&header), sizeof(Header)) != sizeof(Header)) {
		if (outError) *outError = u"Failed to read header."_q;
		return false;
	}

	if (memcmp(header.magic, kBackupMagic, kMagicSize) != 0) {
		if (outError) *outError = u"Invalid magic signature."_q;
		return false;
	}

	const auto cipher = file.read(header.payloadLength);
	if (cipher.size() != int(header.payloadLength)) {
		if (outError) *outError = u"Truncated payload."_q;
		return false;
	}

	DerivedKeys keys;
	if (!DeriveKeys(passcode, header.salt, kSaltSize, &keys)) {
		if (outError) *outError = u"Key derivation failed."_q;
		return false;
	}

	auto hmacTarget = QByteArray();
	hmacTarget.append(reinterpret_cast<const char*>(&header), offsetof(Header, hmac));
	hmacTarget.append(cipher);

	const auto computedHmac = ComputeHmac(
		keys.hmacKey,
		kAesKeySize,
		reinterpret_cast<const uint8_t*>(hmacTarget.constData()),
		hmacTarget.size());
	OPENSSL_cleanse(&keys, sizeof(keys));

	const auto valid = (computedHmac.size() == kHmacSize)
		&& (CRYPTO_memcmp(computedHmac.constData(), header.hmac, kHmacSize) == 0);

	if (!valid && outError) {
		*outError = u"Invalid password or corrupted backup file."_q;
	}
	return valid;
}

} // namespace AyuBackup
