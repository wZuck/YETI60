# SPDX-License-Identifier: MIT
# Root-relative inputs keep normal/calibrator and isolated candidate builds
# consistent; console/keymap-only differences do not describe the EC signal.
function(yeti60_calibration_contract root output)
  set(inputs
    firmware/yeti60/board_pins.h
    firmware/yeti60/core.c
    firmware/yeti60/core.h
    firmware/yeti60/calibration.c
    firmware/yeti60/calibration.h
    firmware/target/src/scanner.c
    firmware/target/src/gpio_modes.h
    firmware/target/boards/yeti/yeti60/yeti60.dts
    firmware/target/boards/yeti/yeti60/yeti60_defconfig
    firmware/target/config/yeti60.conf
    firmware/target/config/west.yml
    firmware/target/Kconfig
    firmware/target/CMakeLists.txt
    firmware/target/calibration-contract.cmake
    hardware/ec60-nrf52840/EC60-nRF52840.kicad_pcb)
  set(signature "yeti60-calibration-v3")
  foreach(path IN LISTS inputs)
    file(SHA256 "${root}/${path}" digest)
    string(APPEND signature "\n${path}=${digest}")
  endforeach()
  foreach(option
      CONFIG_YETI60_ACTIVE_SCAN_MS CONFIG_YETI60_IDLE_SCAN_MS
      CONFIG_YETI60_IDLE_AFTER_MS CONFIG_YETI60_AFE_IDLE_GATING)
    if(DEFINED ${option})
      set(value "${${option}}")
    elseif(option STREQUAL "CONFIG_YETI60_AFE_IDLE_GATING")
      set(value "n")
    else()
      message(FATAL_ERROR "Missing calibration scan option: ${option}")
    endif()
    string(APPEND signature "\n${option}=${value}")
  endforeach()
  string(SHA256 digest "${signature}")
  string(SUBSTRING "${digest}" 0 8 version)
  set(${output} "0x${version}" PARENT_SCOPE)
endfunction()
