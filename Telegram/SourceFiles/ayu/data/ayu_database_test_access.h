#pragma once

#include "ayu/libs/sqlite/sqlite3.h"

#include <QtCore/QByteArray>
#include <QtCore/QString>

namespace AyuDatabase::Test {

[[nodiscard]] QByteArray getDatabaseKey();
void setDatabaseKey(const QByteArray &key);

[[nodiscard]] int getDatabaseState();
void setDatabaseState(int state);

[[nodiscard]] bool testDatabaseReady();

[[nodiscard]] bool testHasPlaintextHeader(const QString &path);

void testApplyCodecKey(sqlite3 *db);

} // namespace AyuDatabase::Test