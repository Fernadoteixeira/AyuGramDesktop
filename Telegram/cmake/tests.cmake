# This file is part of Telegram Desktop,
# the official desktop application for the Telegram messaging service.
#
# For license and copyright information please follow this link:
# https://github.com/telegramdesktop/tdesktop/blob/master/LEGAL

add_executable(test_text WIN32)
init_target(test_text "(tests)")

target_include_directories(test_text PRIVATE ${src_loc})

nice_target_sources(test_text ${src_loc}
PRIVATE
    tests/test_main.cpp
    tests/test_main.h
    tests/test_text.cpp
)

nice_target_sources(test_text ${res_loc}
PRIVATE
    qrc/emoji_1.qrc
    qrc/emoji_2.qrc
    qrc/emoji_3.qrc
    qrc/emoji_4.qrc
    qrc/emoji_5.qrc
    qrc/emoji_6.qrc
    qrc/emoji_7.qrc
    qrc/emoji_8.qrc
)

target_link_libraries(test_text
PRIVATE
    desktop-app::lib_base
    desktop-app::lib_crl
    desktop-app::lib_ui
    desktop-app::external_qt
    desktop-app::external_qt_static_plugins
)

set_target_properties(test_text PROPERTIES RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR})

add_dependencies(Telegram test_text)

target_prepare_qrc(test_text)

if (UNIX AND NOT APPLE)
    add_executable(test_storage_kdf)
    init_target(test_storage_kdf "(security tests)")
    target_include_directories(test_storage_kdf PRIVATE ${src_loc})
    nice_target_sources(test_storage_kdf ${src_loc}
    PRIVATE
        storage/details/storage_file_utilities.cpp
        storage/details/storage_file_utilities_kdf_test.cpp
    )
    target_compile_options(test_storage_kdf PRIVATE -ffunction-sections -fdata-sections)
    target_link_options(test_storage_kdf PRIVATE -Wl,--gc-sections -Wl,--wrap=EVP_PBE_scrypt)
    target_link_libraries(test_storage_kdf
    PRIVATE
        tdesktop::td_mtproto
        desktop-app::lib_base
        desktop-app::lib_crl
        desktop-app::lib_storage
        desktop-app::external_openssl
        desktop-app::external_qt
        desktop-app::external_zlib
    )
    set_target_properties(test_storage_kdf PROPERTIES RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR})

    add_executable(test_ayu_database)
    init_target(test_ayu_database "(security tests)")
    target_include_directories(test_ayu_database PRIVATE ${src_loc})
    nice_target_sources(test_ayu_database ${src_loc}
    PRIVATE
        ayu/data/ayu_database.cpp
        ayu/data/ayu_database_test.cpp
        ayu/libs/sqlite/sqlite3.c
    )
    target_compile_options(test_ayu_database PRIVATE -ffunction-sections -fdata-sections)
    target_compile_definitions(test_ayu_database PRIVATE AYU_DATABASE_TEST_BUILD)
    target_link_options(test_ayu_database PRIVATE -Wl,--gc-sections)
    target_link_libraries(test_ayu_database
    PRIVATE
        tdesktop::td_mtproto
        desktop-app::lib_base
        desktop-app::lib_crl
        desktop-app::lib_storage
        desktop-app::external_openssl
        desktop-app::external_qt
        desktop-app::external_zlib
    )
    set_target_properties(test_ayu_database PROPERTIES RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR})
endif()
