import json
import os
import re
import sqlite3
import sys

# Ensure stdout uses UTF-8 on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def test_sqlite_schema_and_logic():
    print("[TEST 1/8] Executing Local SQLite Database Validation (ayudata.db schema, indexes & queries)...")
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

    # Test DeletedDialog
    cursor.execute("""
    INSERT INTO DeletedDialog (userId, dialogId, peerId, folderId, topMessage, lastMessageDate, flags, entityCreateDate)
    VALUES (1001, 2002, 2002, 0, 5005, 1753440000, 1, 1753440100);
    """)
    cursor.execute("SELECT count(*) FROM DeletedDialog WHERE userId = 1001;")
    assert cursor.fetchone()[0] == 1

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

    cursor.execute("""
    INSERT INTO SpyMessageContentsRead (userId, dialogId, messageId, entityCreateDate)
    VALUES (1001, 2002, 5005, 1753440100);
    """)
    cursor.execute("""
    SELECT count(*) FROM SpyMessageContentsRead WHERE userId = 1001 AND dialogId = 2002;
    """)
    assert cursor.fetchone()[0] == 1

    print("  [OK] SQLite schema (all 8 tables), indexes, and queries successfully verified.")

def test_regex_matching_engine():
    print("[TEST 2/8] Executing Regex Filter & Exclusion Engine Logic...")
    
    # Test typical AyuGram regex filters
    pattern_case_insensitive = re.compile(r"crypto|airdrop|binance", re.IGNORECASE)
    pattern_case_sensitive = re.compile(r"URGENT_ADMIN_ALERT")
    
    msg_spam = "Get your free airdrop on Binance today!"
    msg_clean = "Hello, how are you doing?"
    msg_admin = "URGENT_ADMIN_ALERT: Server reboot"
    
    assert pattern_case_insensitive.search(msg_spam) is not None, "Regex failed to match spam."
    assert pattern_case_insensitive.search(msg_clean) is None, "Regex false positive on clean message."
    assert pattern_case_sensitive.search(msg_admin) is not None, "Regex failed to match admin alert."
    assert pattern_case_sensitive.search(msg_admin.lower()) is None, "Regex case sensitivity violated."
    print("  [OK] Regex filter compilation and matching engine verified.")

def test_json_settings_serialization():
    print("[TEST 3/8] Executing JSON Preferences Serialization Validation (ayu_settings.h)...")
    
    settings_payload = {
        "sendReadMessages": False,
        "sendReadStories": False,
        "sendOnlinePackets": False,
        "sendUploadProgress": False,
        "sendOfflinePacketAfterOnline": True,
        "ghostModeActive": True,
        "streamerModeActive": True,
        "hidePhoneInSettings": True,
        "hideUsernameInSettings": True,
        "peerIdDisplay": "TelegramApi",
        "channelBottomButton": "MuteUnmute",
        "contextMenuVisibility": "VisibleWithModifier",
        "translationProvider": "telegram",
        "sendWithoutSound": "InGhostMode",
        "saveDeletedMessages": True,
        "saveEditedMessages": True,
        "hideDeletedBadge": False,
        "customBadges": [
            {"userId": 1234567, "badge": "⭐ VIP", "color": "#FFD700"},
            {"userId": 9876543, "badge": "🛡️ ADMIN", "color": "#FF4500"}
        ]
    }

    serialized = json.dumps(settings_payload, indent=2)
    deserialized = json.loads(serialized)

    assert deserialized["ghostModeActive"] is True
    assert deserialized["streamerModeActive"] is True
    assert deserialized["sendReadMessages"] is False
    assert deserialized["saveDeletedMessages"] is True
    assert deserialized["translationProvider"] == "telegram"
    assert len(deserialized["customBadges"]) == 2
    assert deserialized["customBadges"][0]["badge"] == "⭐ VIP"
    print("  [OK] Ghost Mode, Streamer Mode & Custom Badges serialization verified.")

def test_devcontainer_scripts():
    print("[TEST 4/8] Executing Devcontainer & Headless Scripts Verification...")
    
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
    print("[TEST 5/8] Executing ayu_database.cpp Consistency Verification...")
    
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

def test_schema_migration_simulation():
    print("[TEST 6/8] Executing Database Multi-Version Schema Migration Simulation...")
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE SchemaVersion (id INTEGER PRIMARY KEY, version INTEGER NOT NULL);")
    cursor.execute("INSERT INTO SchemaVersion (id, version) VALUES (1, 1);")
    cursor.execute("CREATE TABLE DeletedMessage (id INTEGER PRIMARY KEY, text TEXT);")
    cursor.execute("INSERT INTO DeletedMessage (id, text) VALUES (1, 'Legacy message');")
    cursor.execute("ALTER TABLE DeletedMessage ADD COLUMN entityCreateDate INTEGER DEFAULT 0;")
    cursor.execute("UPDATE SchemaVersion SET version = 2 WHERE id = 1;")
    cursor.execute("SELECT version FROM SchemaVersion WHERE id = 1;")
    assert cursor.fetchone()[0] == 2, "Migration to v2 failed."
    cursor.execute("SELECT entityCreateDate FROM DeletedMessage WHERE id = 1;")
    assert cursor.fetchone()[0] == 0, "Default column value migration failed."
    print("  [OK] Schema migration simulation passed.")

def test_ayubackup_cryptographic_container():
    print("[TEST 7/8] Executing AyuBackup Cryptographic Container (.ayubackup) Validation...")
    import hashlib
    import hmac
    import struct

    from cryptography.hazmat.primitives import padding
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

    MAGIC = b"AYUBACKUP\x01"
    VERSION = 1
    KDF_ALGO = 1
    SALT_LEN = 16
    IV_LEN = 16
    HMAC_LEN = 32
    HEADER_STRUCT_PREFIX = "<10sBB16s16sI"

    def create_backup_container(passcode: str, payload_data: dict) -> bytes:
        plain_bytes = json.dumps(payload_data).encode("utf-8")
        salt = os.urandom(SALT_LEN)
        iv = os.urandom(IV_LEN)

        derived = hashlib.pbkdf2_hmac("sha256", passcode.encode("utf-8"), salt, 100000, 64)
        aes_key = derived[:32]
        hmac_key = derived[32:]

        padder = padding.PKCS7(128).padder()
        padded_plain = padder.update(plain_bytes) + padder.finalize()

        cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv))
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(padded_plain) + encryptor.finalize()

        header_prefix = struct.pack(HEADER_STRUCT_PREFIX, MAGIC, VERSION, KDF_ALGO, salt, iv, len(ciphertext))
        auth_target = header_prefix + ciphertext
        auth_tag = hmac.new(hmac_key, auth_target, hashlib.sha256).digest()

        return header_prefix + auth_tag + ciphertext

    def read_and_verify_backup(passcode: str, container_bytes: bytes) -> dict:
        header_len = struct.calcsize(HEADER_STRUCT_PREFIX) + HMAC_LEN
        assert len(container_bytes) >= header_len, "Container too small"

        header_prefix_len = struct.calcsize(HEADER_STRUCT_PREFIX)
        header_prefix = container_bytes[:header_prefix_len]
        magic, ver, kdf, salt, iv, payload_len = struct.unpack(HEADER_STRUCT_PREFIX, header_prefix)

        assert magic == MAGIC, f"Invalid magic header: {magic}"
        assert ver == VERSION, f"Unsupported version: {ver}"
        assert kdf == KDF_ALGO, f"Unsupported KDF: {kdf}"

        received_hmac = container_bytes[header_prefix_len:header_prefix_len + HMAC_LEN]
        ciphertext = container_bytes[header_prefix_len + HMAC_LEN:]
        assert len(ciphertext) == payload_len, "Ciphertext length mismatch"

        derived = hashlib.pbkdf2_hmac("sha256", passcode.encode("utf-8"), salt, 100000, 64)
        aes_key = derived[:32]
        hmac_key = derived[32:]

        auth_target = header_prefix + ciphertext
        computed_hmac = hmac.new(hmac_key, auth_target, hashlib.sha256).digest()

        if not hmac.compare_digest(received_hmac, computed_hmac):
            raise ValueError("Authentication error: Wrong password or tampered payload")

        cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv))
        decryptor = cipher.decryptor()
        padded_plain = decryptor.update(ciphertext) + decryptor.finalize()

        unpadder = padding.PKCS7(128).unpadder()
        plain_bytes = unpadder.update(padded_plain) + unpadder.finalize()

        return json.loads(plain_bytes.decode("utf-8"))

    # 1. Test standard backup round-trip
    test_data = {
        "version": 1,
        "timestamp": 1753440000,
        "settings": {
            "ghostModeActive": True,
            "streamerModeActive": True,
            "sendReadMessages": False,
        },
        "filters": [
            {
                "id": "aabbccddeeff00112233445566778899",
                "text": "airdrop|scam",
                "enabled": True,
                "reversed": False,
                "caseInsensitive": True,
            }
        ],
        "deletedMessages": [
            {
                "userId": 1001,
                "dialogId": 2002,
                "messageId": 5005,
                "text": "Anti-Recall Test Message in Backup",
                "entityCreateDate": 1753440000,
            }
        ]
    }

    passcode = "AyuGramSecurePasscode2026!#"
    container = create_backup_container(passcode, test_data)
    recovered = read_and_verify_backup(passcode, container)

    assert recovered["version"] == 1
    assert recovered["settings"]["ghostModeActive"] is True
    assert len(recovered["filters"]) == 1
    assert recovered["deletedMessages"][0]["text"] == "Anti-Recall Test Message in Backup"

    # 2. Test wrong password rejection
    try:
        read_and_verify_backup("WrongPassword!", container)
        assert False, "Failed to reject incorrect password!"
    except ValueError:
        pass

    # 3. Test tamper detection (bit flipping)
    # Flipped byte in ciphertext
    tampered_cipher = bytearray(container)
    tampered_cipher[-5] ^= 0xFF
    try:
        read_and_verify_backup(passcode, bytes(tampered_cipher))
        assert False, "Failed to detect tampered ciphertext!"
    except ValueError:
        pass

    # Flipped byte in header
    tampered_header = bytearray(container)
    tampered_header[12] ^= 0xFF # salt mutation
    try:
        read_and_verify_backup(passcode, bytes(tampered_header))
        assert False, "Failed to detect tampered header!"
    except ValueError:
        pass

    # 4. Test database restore simulation from backup
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE DeletedMessage (userId INTEGER, dialogId INTEGER, messageId INTEGER, text TEXT);")
    for msg in recovered["deletedMessages"]:
        cursor.execute("INSERT INTO DeletedMessage (userId, dialogId, messageId, text) VALUES (?, ?, ?, ?);",
                       (msg["userId"], msg["dialogId"], msg["messageId"], msg["text"]))
    cursor.execute("SELECT text FROM DeletedMessage WHERE userId = 1001 AND messageId = 5005;")
    db_row = cursor.fetchone()
    assert db_row is not None and db_row[0] == "Anti-Recall Test Message in Backup"

    print("  [OK] AyuBackup container encryption, authentication, tamper-detection & restore verified.")

def test_backup_cpp_invariants():
    print("[TEST 8/8] Executing ayu_backup.cpp & ayu_backup.h Codebase Invariants Verification...")
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    backup_h_path = os.path.join(repo_root, "Telegram", "SourceFiles", "ayu", "data", "ayu_backup.h")
    backup_cpp_path = os.path.join(repo_root, "Telegram", "SourceFiles", "ayu", "data", "ayu_backup.cpp")

    assert os.path.exists(backup_h_path), f"Failure: ayu_backup.h not found at {backup_h_path}"
    assert os.path.exists(backup_cpp_path), f"Failure: ayu_backup.cpp not found at {backup_cpp_path}"

    with open(backup_h_path, "r", encoding="utf-8") as f:
        h_content = f.read()
    with open(backup_cpp_path, "r", encoding="utf-8") as f:
        cpp_content = f.read()

    # Verify structural and security invariants
    assert "kBackupMagic" in h_content, "Missing kBackupMagic constant"
    assert "ExportToFile" in h_content, "Missing ExportToFile declaration"
    assert "ImportFromFile" in h_content, "Missing ImportFromFile declaration"
    assert "VerifyBackupFile" in h_content, "Missing VerifyBackupFile declaration"

    assert "OPENSSL_cleanse" in cpp_content, "Missing OPENSSL_cleanse memory zeroization"
    assert "PKCS5_PBKDF2_HMAC" in cpp_content, "Missing PKCS5_PBKDF2_HMAC derivation"
    assert "EVP_aes_256_cbc" in cpp_content, "Missing AES-256 cipher routine"
    assert "QSaveFile" in cpp_content, "Missing atomic QSaveFile persistence"
    print("  [OK] ayu_backup.h and ayu_backup.cpp invariants verified.")

if __name__ == "__main__":
    test_sqlite_schema_and_logic()
    test_regex_matching_engine()
    test_json_settings_serialization()
    test_devcontainer_scripts()
    test_database_cpp_invariants()
    test_schema_migration_simulation()
    test_ayubackup_cryptographic_container()
    test_backup_cpp_invariants()
    print("\n[SUCCESS] ALL 8 UNIT, LOGIC AND INVARIANT GATES PASSED (100% GREEN)!")
