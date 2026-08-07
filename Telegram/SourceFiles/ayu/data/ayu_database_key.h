// This is the source code of AyuGram for Desktop.
//
// We do not and cannot prevent the use of our code,
// but be respectful and credit the original author.
//
// Copyright @Radolyn, 2026
#pragma once

#include <QtCore/QByteArray>

#include <memory>
#include <optional>

namespace MTP {
class AuthKey;
using AuthKeyPtr = std::shared_ptr<AuthKey>;
} // namespace MTP

namespace AyuDatabase {

inline constexpr auto kDatabaseKeySize = 32;

[[nodiscard]] QByteArray generateDatabaseKey();

[[nodiscard]] bool storeDatabaseKey(
	const QByteArray &key,
	const MTP::AuthKeyPtr &localKey);

[[nodiscard]] std::optional<QByteArray> loadDatabaseKey(
	const MTP::AuthKeyPtr &localKey);

}
