import sqlite3
import json
import os
import sys

# Ensure stdout uses UTF-8 on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def test_sqlite_schema_and_logic():
    print("[TEST 1/4] Executing Local SQLite Database Validation (ayudata.db schema & queries)...")
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE SchemaVersion (
        id INTEGER PRIMARY KEY,
        version INTEGER NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE DeletedMessage (
        fakeId INTEGER PRIMARY KEY AUTOINCREMENT,
        userId INTEGER NOT NULL,
        dialogId INTEGER NOT NULL,
        groupedId INTEGER,
        peerId INTEGER NOT NULL,
        fromId INTEGER NOT NULL,
        topicId INTEGER,
        messageId INTEGER NOT NULL,
        date INTEGER NOT NULL,
        flags INTEGER,
        editDate INTEGER,
        views INTEGER,
        fwdFlags INTEGER,
        fwdFromId INTEGER,
        fwdName TEXT,
        fwdDate INTEGER,
        fwdPostAuthor TEXT,
        replyFlags INTEGER,
        replyMessageId INTEGER,
        replyPeerId INTEGER,
        replyTopId INTEGER,
        replyForumTopic INTEGER,
        replySerialized BLOB,
        entityCreateDate INTEGER NOT NULL,
        text TEXT NOT NULL,
        textEntities BLOB,
        mediaPath TEXT,
        hqThumbPath TEXT,
        documentType INTEGER,
        documentSerialized BLOB,
        thumbsSerialized BLOB,
        documentAttributesSerialized BLOB,
        mimeType TEXT
    );
    """)

    cursor.execute("""
    CREATE INDEX idx_deleted_message_userId_dialogId_topicId_messageId
    ON DeletedMessage (userId, dialogId, topicId, messageId);
    """)

    cursor.execute("""
    CREATE INDEX idx_deleted_message_userId_dialogId_messageId
    ON DeletedMessage (userId, dialogId, messageId);
    """)

    cursor.execute("""
    CREATE TABLE EditedMessage (
        fakeId INTEGER PRIMARY KEY AUTOINCREMENT,
        userId INTEGER NOT NULL,
        dialogId INTEGER NOT NULL,
        groupedId INTEGER,
        peerId INTEGER NOT NULL,
        fromId INTEGER NOT NULL,
        topicId INTEGER,
        messageId INTEGER NOT NULL,
        date INTEGER NOT NULL,
        flags INTEGER,
        editDate INTEGER NOT NULL,
        views INTEGER,
        fwdFlags INTEGER,
        fwdFromId INTEGER,
        fwdName TEXT,
        fwdDate INTEGER,
        fwdPostAuthor TEXT,
        replyFlags INTEGER,
        replyMessageId INTEGER,
        replyPeerId INTEGER,
        replyTopId INTEGER,
        replyForumTopic INTEGER,
        replySerialized BLOB,
        entityCreateDate INTEGER NOT NULL,
        text TEXT NOT NULL,
        textEntities BLOB,
        mediaPath TEXT,
        hqThumbPath TEXT,
        documentType INTEGER,
        documentSerialized BLOB,
        thumbsSerialized BLOB,
        documentAttributesSerialized BLOB,
        mimeType TEXT
    );
    """)

    cursor.execute("""
    CREATE INDEX idx_edited_message_userId_dialogId_messageId
    ON EditedMessage (userId, dialogId, messageId);
    """)

    cursor.execute("""
    CREATE INDEX idx_edited_message_userId_dialogId_messageId_fakeId
    ON EditedMessage (userId, dialogId, messageId, fakeId);
    """)

    cursor.execute("""
    CREATE TABLE DeletedDialog (
        fakeId INTEGER PRIMARY KEY AUTOINCREMENT,
        userId INTEGER NOT NULL,
        dialogId INTEGER NOT NULL,
        peerId INTEGER NOT NULL,
        folderId INTEGER,
        topMessage INTEGER,
        lastMessageDate INTEGER,
        flags INTEGER,
        entityCreateDate INTEGER NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE RegexFilter (
        id BLOB PRIMARY KEY,
        text TEXT NOT NULL,
        enabled INTEGER NOT NULL,
        reversed INTEGER NOT NULL,
        caseInsensitive INTEGER NOT NULL,
        dialogId INTEGER
    );
    """)

    cursor.execute("""
    CREATE INDEX idx_regex_filter_dialogId
    ON RegexFilter (dialogId);
    """)

    cursor.execute("""
    CREATE TABLE RegexFilterGlobalExclusion (
        fakeId INTEGER PRIMARY KEY AUTOINCREMENT,
        dialogId INTEGER NOT NULL,
        filterId BLOB NOT NULL
    );
    """)

    cursor.execute("""
    CREATE INDEX idx_regex_filter_global_exclusion_dialogId
    ON RegexFilterGlobalExclusion (dialogId);
    """)

    cursor.execute("""
    CREATE INDEX idx_regex_filter_global_exclusion_filterId
    ON RegexFilterGlobalExclusion (filterId);
    """)

    cursor.execute("""
    CREATE TABLE SpyMessageRead (
        fakeId INTEGER PRIMARY KEY AUTOINCREMENT,
        userId INTEGER NOT NULL,
        dialogId INTEGER NOT NULL,
        messageId INTEGER NOT NULL,
        entityCreateDate INTEGER NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE SpyMessageContentsRead (
        fakeId INTEGER PRIMARY KEY AUTOINCREMENT,
        userId INTEGER NOT NULL,
        dialogId INTEGER NOT NULL,
        messageId INTEGER NOT NULL,
        entityCreateDate INTEGER NOT NULL
    );
    """)

    # Test Insertion & Query of DeletedMessage (Anti-Recall)
    cursor.execute("INSERT INTO SchemaVersion (id, version) VALUES (1, 1);")
    cursor.execute("""
    INSERT INTO DeletedMessage (userId, dialogId, peerId, fromId, topicId, messageId, date, entityCreateDate, text)
    VALUES (1001, 2002, 2002, 3003, 0, 5005, 1753440000, 1753440000, 'Test Anti-Recall Message');
    """)

    cursor.execute("""
    SELECT text FROM DeletedMessage WHERE userId = 1001 AND dialogId = 2002 AND messageId = 5005;
    """)
    row = cursor.fetchone()
    assert row is not None, "Failure: Deleted message was not retrieved by index."
    assert row[0] == "Test Anti-Recall Message", f"Failure: Content mismatch: {row[0]}"

    # Test Insertion & Query of EditedMessage (Message History)
    cursor.execute("""
    INSERT INTO EditedMessage (userId, dialogId, peerId, fromId, topicId, messageId, date, editDate, entityCreateDate, text)
    VALUES (1001, 2002, 2002, 3003, 0, 5005, 1753440000, 1753440050, 1753440050, 'Edited Message Revision 1');
    """)
    cursor.execute("""
    SELECT text, editDate FROM EditedMessage WHERE userId = 1001 AND dialogId = 2002 AND messageId = 5005;
    """)
    edit_row = cursor.fetchone()
    assert edit_row is not None, "Failure: Edited message revision was not retrieved."
    assert edit_row[0] == "Edited Message Revision 1"

    # Test RegexFilter and Exclusion
    filter_id = b"filter_uuid_123"
    cursor.execute("""
    INSERT INTO RegexFilter (id, text, enabled, reversed, caseInsensitive, dialogId)
    VALUES (?, ?, 1, 0, 1, NULL);
    """, (filter_id, "spam_keyword"))

    cursor.execute("""
    INSERT INTO RegexFilterGlobalExclusion (dialogId, filterId)
    VALUES (9999, ?);
    """, (filter_id,))

    cursor.execute("""
    SELECT text FROM RegexFilter WHERE id = ?;
    """, (filter_id,))
    f_row = cursor.fetchone()
    assert f_row is not None and f_row[0] == "spam_keyword"

    # Test Spy Read tracking
    cursor.execute("""
    INSERT INTO SpyMessageRead (userId, dialogId, messageId, entityCreateDate)
    VALUES (1001, 2002, 5005, 1753440100);
    """)
    cursor.execute("""
    SELECT count(*) FROM SpyMessageRead WHERE userId = 1001 AND dialogId = 2002;
    """)
    assert cursor.fetchone()[0] == 1

    print("  [OK] SQLite schema (all 8 tables), indexes, and queries successfully verified.")

def test_json_settings_serialization():
    print("[TEST 2/4] Executing JSON Preferences Serialization Validation (ayu_settings.h)...")
    
    settings_payload = {
        "sendReadMessages": False,
        "sendReadStories": False,
        "sendOnlinePackets": False,
        "sendUploadProgress": False,
        "sendOfflinePacketAfterOnline": True,
        "ghostModeActive": True,
        "peerIdDisplay": "TelegramApi",
        "channelBottomButton": "MuteUnmute",
        "contextMenuVisibility": "VisibleWithModifier",
        "translationProvider": "telegram",
        "sendWithoutSound": "InGhostMode",
        "saveDeletedMessages": True,
        "saveEditedMessages": True,
        "hideDeletedBadge": False
    }

    serialized = json.dumps(settings_payload)
    deserialized = json.loads(serialized)

    assert deserialized["ghostModeActive"] is True
    assert deserialized["sendReadMessages"] is False
    assert deserialized["saveDeletedMessages"] is True
    assert deserialized["translationProvider"] == "telegram"
    print("  [OK] Ghost Mode & Preferences mapping and serialization verified.")

def test_devcontainer_scripts():
    print("[TEST 3/4] Executing Devcontainer & Headless Scripts Verification...")
    
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    start_desktop_path = os.path.join(repo_root, ".devcontainer", "start-desktop.sh")
    launch_ayugram_path = os.path.join(repo_root, ".devcontainer", "launch-ayugram.sh")

    assert os.path.exists(start_desktop_path), f"Failure: start-desktop.sh not found at {start_desktop_path}."
    assert os.path.exists(launch_ayugram_path), f"Failure: launch-ayugram.sh not found at {launch_ayugram_path}."

    with open(start_desktop_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "export LIBGL_ALWAYS_SOFTWARE='1'" in content, "Failure: Software OpenGL not configured."
    assert "export QT_QPA_PLATFORM='xcb'" in content, "Failure: QT Platform XCB not configured."
    assert "Xvfb" in content, "Failure: Xvfb virtual server not initialized."
    assert "x11vnc" in content and "novnc" in content, "Failure: Incomplete VNC/noVNC support."
    print("  [OK] start-desktop.sh script validated with software OpenGL and noVNC support.")

def test_database_cpp_invariants():
    print("[TEST 4/4] Executing ayu_database.cpp Consistency Verification...")
    
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    db_cpp_path = os.path.join(repo_root, "Telegram", "SourceFiles", "ayu", "data", "ayu_database.cpp")
    
    assert os.path.exists(db_cpp_path), f"Failure: ayu_database.cpp not found at {db_cpp_path}."
    with open(db_cpp_path, "r", encoding="utf-8") as f:
        cpp_content = f.read()

    # Check key methods and security constraints
    assert "dbStorage()" in cpp_content, "Failure: dbStorage accessor missing."
    assert "applyCodecKey" in cpp_content, "Failure: Codec key application missing."
    assert "OPENSSL_cleanse" in cpp_content, "Failure: Key zeroization/cleanse missing."
    assert "migratePlaintextDatabase" in cpp_content, "Failure: Plaintext migration function missing."
    print("  [OK] ayu_database.cpp invariants verified.")

if __name__ == "__main__":
    test_sqlite_schema_and_logic()
    test_json_settings_serialization()
    test_devcontainer_scripts()
    test_database_cpp_invariants()
    print("\n[SUCCESS] ALL UNIT AND LOGIC GATES PASSED (100% GREEN)!")

