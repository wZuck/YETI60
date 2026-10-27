/* YETI60 portable nRF52840 control core. SPDX-License-Identifier: MIT */
#pragma once
#include "board_pins.h"
#include <stdbool.h>
#include <stdint.h>
enum yeti_mode { Y_HIZ, Y_LOW, Y_HIGH, Y_OD_LOW, Y_OD_RELEASE };
enum yeti_usb { Y_USB_OFF, Y_USB_POWERED, Y_USB_CONFIGURED, Y_USB_SUSPENDED };
enum yeti_link { Y_NONE, Y_USB, Y_BLE };
struct yeti_hal {
  void *ctx;
  void (*gpio)(void *, uint8_t, enum yeti_mode);
  void (*wait_us)(void *, uint32_t);
  int (*adc)(void *, uint8_t, uint32_t);
  bool (*report)(void *, enum yeti_link, const uint8_t[8]);
};
struct yeti_config {
  uint16_t low[YETI_ROWS][YETI_COLS], high[YETI_ROWS][YETI_COLS];
  uint8_t usage[YETI_ROWS]
               [YETI_COLS]; /* Board layout mapping, not calibration. */
  uint8_t debounce_frames;
  uint32_t afe_settle_us, mux_settle_us, discharge_us, charge_us,
      acquisition_us;
};
struct yeti_core {
  struct yeti_hal hal;
  struct yeti_config cfg;
  uint16_t matrix[YETI_ROWS];
  uint8_t count[YETI_ROWS][YETI_COLS];
  uint8_t last_report[8];
  uint8_t pending_release; /* Transport bitmask; retry old-host key releases. */
  enum yeti_link link;
  bool initialized, powered, busy, dirty;
};
int yeti_init(struct yeti_core *, const struct yeti_hal *,
              const struct yeti_config *);
int yeti_power(struct yeti_core *, bool);
int yeti_scan(struct yeti_core *);
int yeti_battery_mv(struct yeti_core *, uint32_t *);
int yeti_connections(struct yeti_core *, enum yeti_usb, unsigned host_ma,
                     bool ble_connected);
