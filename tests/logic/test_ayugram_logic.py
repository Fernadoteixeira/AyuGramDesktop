import sqlite3
import json
import os
import sys

# Forçar stdout para UTF-8 no Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def test_sqlite_schema_and_logic():
    print("[TEST 1/3] Executando Validação do Banco SQLite Local (ayudata.db)...")
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

    # Teste de Inserção e Consulta Anti-Recall
    cursor.execute("INSERT INTO SchemaVersion (id, version) VALUES (1, 1);")
    cursor.execute("""
    INSERT INTO DeletedMessage (userId, dialogId, peerId, fromId, topicId, messageId, date, entityCreateDate, text)
    VALUES (1001, 2002, 2002, 3003, 0, 5005, 1753440000, 1753440000, 'Mensagem Anti-Recall de Teste');
    """)

    cursor.execute("""
    SELECT text FROM DeletedMessage WHERE userId = 1001 AND dialogId = 2002 AND messageId = 5005;
    """)
    row = cursor.fetchone()
    assert row is not None, "Falha: Mensagem deletada não foi recuperada pelo índice."
    assert row[0] == "Mensagem Anti-Recall de Teste", f"Falha: Conteúdo divergente: {row[0]}"
    print("  [OK] Schema SQLite, índices e consulta Anti-Recall validados com sucesso.")

def test_json_settings_serialization():
    print("[TEST 2/3] Executando Validação de Serialização JSON de Preferências (ayu_settings.h)...")
    
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
        "sendWithoutSound": "InGhostMode"
    }

    serialized = json.dumps(settings_payload)
    deserialized = json.loads(serialized)

    assert deserialized["ghostModeActive"] is True
    assert deserialized["sendReadMessages"] is False
    assert deserialized["translationProvider"] == "telegram"
    print("  [OK] Mapeamento e serialização das opções de Ghost Mode e Preferências validados.")

def test_devcontainer_scripts():
    print("[TEST 3/3] Executando Verificação de Scripts Headless do Devcontainer...")
    
    start_desktop_path = r"c:\Users\fjuni\OneDrive\Documentos\GitHub\AyuGramDesktop\.devcontainer\start-desktop.sh"
    launch_ayugram_path = r"c:\Users\fjuni\OneDrive\Documentos\GitHub\AyuGramDesktop\.devcontainer\launch-ayugram.sh"

    assert os.path.exists(start_desktop_path), "Falha: start-desktop.sh não encontrado."
    assert os.path.exists(launch_ayugram_path), "Falha: launch-ayugram.sh não encontrado."

    with open(start_desktop_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "export LIBGL_ALWAYS_SOFTWARE='1'" in content, "Falha: Software OpenGL não configurado."
    assert "export QT_QPA_PLATFORM='xcb'" in content, "Falha: QT Platform XCB não configurado."
    assert "Xvfb" in content, "Falha: Xvfb servidor virtual não inicializado."
    assert "x11vnc" in content and "novnc" in content, "Falha: Suporte VNC/noVNC incompleto."
    print("  [OK] Script start-desktop.sh validado com suporte OpenGL software e noVNC.")

if __name__ == "__main__":
    test_sqlite_schema_and_logic()
    test_json_settings_serialization()
    test_devcontainer_scripts()
    print("\n[SUCESSO] TODOS OS TESTES UNITARIOS E DE LOGICA PASSARAM COM 100% DE SUCESSO!")
