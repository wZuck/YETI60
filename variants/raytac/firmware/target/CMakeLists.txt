zephyr_library()
zephyr_library_sources_ifdef(CONFIG_YETI60_SCAN src/scanner.c src/usb_policy.c ../yeti60/core.c ../yeti60/calibration.c)
zephyr_include_directories(../yeti60)

zephyr_library_include_directories(${APPLICATION_SOURCE_DIR}/include)

# Include the actual waveform/SAADC implementation and effective scan options.
include(${CMAKE_CURRENT_SOURCE_DIR}/calibration-contract.cmake)
yeti60_calibration_contract(${CMAKE_CURRENT_SOURCE_DIR}/../.. calibration_version)
zephyr_library_compile_definitions(YETI_CALIBRATION_VERSION=${calibration_version})
