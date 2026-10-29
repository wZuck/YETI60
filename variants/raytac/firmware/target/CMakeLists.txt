zephyr_library()
zephyr_library_sources_ifdef(CONFIG_YETI60_SCAN src/scanner.c ../yeti60/core.c)
zephyr_include_directories(../yeti60)

zephyr_library_include_directories(${APPLICATION_SOURCE_DIR}/include)

# Settings survive reflashing; reject thresholds from a different pin/board contract.
file(SHA256 ${CMAKE_CURRENT_SOURCE_DIR}/../yeti60/board_pins.h pin_hash)
file(SHA256 ${CMAKE_CURRENT_SOURCE_DIR}/boards/yeti/yeti60/yeti60.dts board_hash)
string(SHA256 calibration_hash "calibration-v1:${pin_hash}:${board_hash}")
string(SUBSTRING ${calibration_hash} 0 8 calibration_version)
zephyr_library_compile_definitions(YETI_CALIBRATION_VERSION=0x${calibration_version})
