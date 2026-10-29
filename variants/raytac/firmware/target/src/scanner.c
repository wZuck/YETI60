/* SPDX-License-Identifier: MIT */
#define DT_DRV_COMPAT yeti_ec60
#include "core.h"
#include "calibration.h"
#include <errno.h>
#include <stdlib.h>
#include <string.h>
#include <zephyr/device.h>
#include <zephyr/drivers/adc.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/drivers/kscan.h>
#include <zephyr/kernel.h>
#include <zephyr/settings/settings.h>
#include <zephyr/shell/shell.h>
#include <zephyr/sys/util.h>
#include <zmk/usb.h>

static struct yeti_core core;
static const struct device *scan_device;
static kscan_callback_t callback;
static atomic_t enabled;
static bool io_fault;
static bool calibrated;
static atomic_t calibration_command;
static atomic_t calibration_loaded;
static uint16_t raw[5][15];
static struct yeti_cal_stats released[5][15], pressed[5][15];
static const uint16_t active[5] = {0x7fff, 0x3fff, 0x2fff, 0x6ffd, 0x0646};
static unsigned pressed_row, pressed_col;
static bool calibration_started;
static unsigned cursor;
static int calibration_mode;
static bool idle_scan;
static bool afe_asleep;
static int64_t idle_since;
struct calibration {
  uint32_t version;
  uint16_t low[5][15], high[5][15];
};
static struct calibration saved;
static int load_calibration(const char *name, size_t len, settings_read_cb read,
                            void *arg) {
  if (strcmp(name, "thresholds"))
    return -ENOENT;
  if (len != sizeof(saved))
    return -EINVAL;
  struct calibration value;
  if (read(arg, &value, sizeof(value)) != sizeof(value) || value.version != YETI_CALIBRATION_VERSION)
    return -EINVAL;
  for (unsigned r = 0; r < 5; r++)
    for (unsigned c = 0; c < 15; c++)
      if (value.low[r][c] >= value.high[r][c] || value.high[r][c] > 4095)
        return -EINVAL;
  saved = value;
  atomic_set(&calibration_loaded, 1);
  return 0;
}
SETTINGS_STATIC_HANDLER_DEFINE(yeti60, "yeti60", NULL, load_calibration, NULL,
                               NULL);
static int __unused command(const struct shell *shell, size_t argc,
                            char **argv) {
  unsigned action = 0;
  if (argc == 2 && !strcmp(argv[1], "release"))
    action = 1;
  else if (argc == 4 && !strcmp(argv[1], "press")) {
    char *end;
    unsigned long row = strtoul(argv[2], &end, 10);
    if (end == argv[2] || *end || row >= 5)
      return -EINVAL;
    unsigned long col = strtoul(argv[3], &end, 10);
    if (end == argv[3] || *end || col >= 15 || !(active[row] & BIT(col)))
      return -EINVAL;
    action = 2 | ((row * 15 + col) << 8);
  } else if (argc == 2 && !strcmp(argv[1], "save"))
    action = 3;
  else if (argc == 2 && !strcmp(argv[1], "status"))
    action = 4;
  else
    return -EINVAL;
  if (!atomic_cas(&calibration_command, 0, action))
    return -EBUSY;
  shell_print(shell, "Queued: hold the selected key BEFORE press row col; "
                     "keep it held until capture completes. Use status for bounds.");
  return 0;
}
#if defined(CONFIG_SHELL)
SHELL_CMD_ARG_REGISTER(yeti_calibrate, NULL,
                       "release | press row col | status | save", command, 2, 2);
#endif

static const struct device *const ports[] = {
    DEVICE_DT_GET(DT_NODELABEL(gpio0)), DEVICE_DT_GET(DT_NODELABEL(gpio1))};
static const struct device *const saadc = DEVICE_DT_GET(DT_NODELABEL(adc));
static void gpio(void *ctx, uint8_t pin, enum yeti_mode mode) {
  ARG_UNUSED(ctx);
  gpio_flags_t flags = mode == Y_HIZ || mode == Y_OD_RELEASE ? GPIO_INPUT
                       : mode == Y_HIGH                      ? GPIO_OUTPUT_HIGH
                                                             : GPIO_OUTPUT_LOW;
  if (gpio_pin_configure(ports[pin / 32], pin % 32, flags))
    io_fault = true;
}
static void wait_us(void *ctx, uint32_t us) {
  ARG_UNUSED(ctx);
  k_busy_wait(us);
}
static int sample(void *ctx, uint8_t ain, uint32_t acquisition) {
  ARG_UNUSED(ctx);
  if (io_fault)
    return -EIO;
  struct adc_channel_cfg channel = {
      .gain = ADC_GAIN_1_6,
      .reference = ADC_REF_INTERNAL,
      .acquisition_time = ADC_ACQ_TIME(ADC_ACQ_TIME_MICROSECONDS, acquisition),
      .channel_id = 0,
      .input_positive = ain + 1,
  };
  int err = adc_channel_setup(saadc, &channel);
  int16_t value;
  struct adc_sequence seq = {.channels = BIT(0),
                             .buffer = &value,
                             .buffer_size = sizeof(value),
                             .resolution = 12};
  if (err)
    return err;
  err = adc_read(saadc, &seq);
  if (!err && ain == YETI_ADC_AIN && cursor < 75) {
    raw[cursor % 5][cursor / 5] = value;
    cursor++;
  }
  return err ? err : value;
}
static bool unused_report(void *ctx, enum yeti_link link,
                          const uint8_t report[8]) {
  ARG_UNUSED(ctx);
  ARG_UNUSED(link);
  ARG_UNUSED(report);
  /* ZMK owns HID delivery; this core callback only acknowledges consumption. */
  return true;
}
static void run(void *a, void *b, void *c) {
  ARG_UNUSED(a);
  ARG_UNUSED(b);
  ARG_UNUSED(c);
  uint16_t previous[YETI_ROWS] = {0};
  enum usb_dc_status_code old = USB_DC_UNKNOWN;
  idle_since = k_uptime_get();
  while (true) {
    if (scan_device == NULL) {
      k_sleep(K_MSEC(20));
      continue;
    }
    if (atomic_cas(&calibration_loaded, 1, 0)) {
      memcpy(core.cfg.low, saved.low, sizeof(saved.low));
      memcpy(core.cfg.high, saved.high, sizeof(saved.high));
      memset(core.matrix, 0, sizeof(core.matrix));
      memset(core.count, 0, sizeof(core.count));
      calibrated = true;
    }
    int action = atomic_set(&calibration_command, 0);
    if ((action & 255) == 1) {
      calibrated = false;
      calibration_started = true;
      calibration_mode = 1;
      for (unsigned r = 0; r < 5; r++)
        for (unsigned c = 0; c < 15; c++) {
          yeti_cal_reset(&released[r][c]);
          yeti_cal_reset(&pressed[r][c]);
        }
    } else if ((action & 255) == 2) {
      bool ready = calibration_started && calibration_mode == 0;
      for (unsigned r = 0; r < 5; r++)
        for (unsigned c = 0; c < 15; c++)
          if ((active[r] & BIT(c)) &&
              released[r][c].count < YETI_CAL_CAPTURE_SAMPLES)
            ready = false;
      unsigned index = (unsigned)action >> 8;
      if (ready && index < 75 && (active[index / 15] & BIT(index % 15))) {
        pressed_row = index / 15;
        pressed_col = index % 15;
        yeti_cal_reset(&pressed[pressed_row][pressed_col]);
        calibrated = false;
        calibration_mode = 2;
      } else
        printk("YETI60: wait for release/current key capture to complete.\n");
    } else if ((action & 255) == 3) {
      struct calibration candidate = {.version = YETI_CALIBRATION_VERSION};
      bool valid = calibration_started && calibration_mode == 0;
      for (unsigned r = 0; r < 5; r++)
        for (unsigned c = 0; c < 15; c++) {
          uint16_t guard;
          candidate.low[r][c] = 4094;
          candidate.high[r][c] = 4095;
          if ((active[r] & BIT(c)) &&
              !yeti_cal_thresholds(&released[r][c], &pressed[r][c],
                                   &candidate.low[r][c], &candidate.high[r][c],
                                   &guard)) {
            valid = false;
            printk("YETI60 rejected key %u,%u: samples/margin/saturation\n", r, c);
          }
        }
      bool saved_ok = false;
      if (valid && !settings_save_one("yeti60/thresholds", &candidate, sizeof(candidate))) {
        saved_ok = true;
        saved = candidate;
        memcpy(core.cfg.low, saved.low, sizeof(saved.low));
        memcpy(core.cfg.high, saved.high, sizeof(saved.high));
        memset(core.matrix, 0, sizeof(core.matrix));
        memset(core.count, 0, sizeof(core.count));
        calibrated = true;
      }
      printk("YETI60 calibration %s\n", saved_ok ? "saved" : "rejected; inspect status and recapture");
    } else if ((action & 255) == 4) {
      printk("key,row,col,release_n,release_min,release_max,press_n,press_min,press_max,low,high,guard,valid\n");
      for (unsigned r = 0; r < 5; r++)
        for (unsigned c = 0; c < 15; c++) {
          if (!(active[r] & BIT(c)))
            continue;
          uint16_t low = 0, high = 0, guard = 0;
          bool valid = yeti_cal_thresholds(&released[r][c], &pressed[r][c], &low, &high, &guard);
          printk("key,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u\n", r, c,
                 released[r][c].count, released[r][c].minimum, released[r][c].maximum,
                 pressed[r][c].count, pressed[r][c].minimum, pressed[r][c].maximum,
                 low, high, guard, valid ? 1u : 0u);
        }
    }
    enum usb_dc_status_code usb = zmk_usb_get_status();
    if (usb != old) {
      enum yeti_usb state = usb == USB_DC_SUSPEND ? Y_USB_SUSPENDED
                            : zmk_usb_is_hid_ready() ? Y_USB_CONFIGURED
                            : (usb == USB_DC_DISCONNECTED || usb == USB_DC_UNKNOWN)
                                ? Y_USB_OFF : Y_USB_POWERED;
      /* Legacy Zephyr bMaxPower uses 2 mA units. Resume preserves the
       * accepted configuration; suspend/reset never enables charging. */
      yeti_connections(&core, state, CONFIG_USB_MAX_POWER * 2, false);
      old = usb;
    }
    if (atomic_get(&enabled)) {
      if (afe_asleep && yeti_afe(&core, true) == 0)
        afe_asleep = false;
      cursor = 0;
      int err = afe_asleep ? -1 : yeti_scan(&core);
      if (!err && calibration_mode == 1) {
        for (unsigned r = 0; r < 5; r++)
          for (unsigned c = 0; c < 15; c++)
            yeti_cal_add(&released[r][c], raw[r][c]);
        if (released[0][0].count >= YETI_CAL_CAPTURE_SAMPLES) {
          calibration_mode = 0;
          printk("YETI60 release capture complete; 128 frames.\n");
        }
      } else if (!err && calibration_mode == 2) {
        struct yeti_cal_stats *stats = &pressed[pressed_row][pressed_col];
        yeti_cal_add(stats, raw[pressed_row][pressed_col]);
        if (stats->count >= YETI_CAL_CAPTURE_SAMPLES) {
          calibration_mode = 0;
          printk("YETI60 press capture complete %u,%u: n=%u min=%u max=%u\n",
                 pressed_row, pressed_col, stats->count, stats->minimum, stats->maximum);
        }
      }
      if (!calibrated)
        memset(core.matrix, 0, sizeof(core.matrix));
      bool changed = false;
      for (unsigned row = 0; row < YETI_ROWS; row++) {
        uint16_t bits = previous[row] ^ core.matrix[row];
        changed |= bits != 0;
        for (unsigned col = 0; col < YETI_COLS; col++)
          if ((bits & BIT(col)) && callback)
            callback(scan_device, row, col, (core.matrix[row] & BIT(col)) != 0);
        previous[row] = core.matrix[row];
      }
      bool any_key = false;
      for (unsigned row = 0; row < YETI_ROWS; row++)
        any_key |= core.matrix[row] != 0;
      if (any_key || changed || calibration_mode) {
        idle_since = k_uptime_get();
        idle_scan = false;
      } else if (!idle_scan &&
                 k_uptime_get() - idle_since >= CONFIG_YETI60_IDLE_AFTER_MS) {
        idle_scan = true;
      }
      if (!err && !io_fault && idle_scan && !any_key && !calibration_mode &&
          IS_ENABLED(CONFIG_YETI60_AFE_IDLE_GATING)) {
        if (yeti_afe(&core, false) == 0)
          afe_asleep = true;
      }
      if (err || io_fault) {
        yeti_power(&core, false);
        afe_asleep = false;
        idle_scan = false;
        k_sleep(K_MSEC(100));
      }
    } else if (!afe_asleep && IS_ENABLED(CONFIG_YETI60_AFE_IDLE_GATING)) {
      if (yeti_afe(&core, false) == 0)
        afe_asleep = true;
    }
    k_sleep(K_MSEC(idle_scan ? CONFIG_YETI60_IDLE_SCAN_MS
                             : CONFIG_YETI60_ACTIVE_SCAN_MS));
  }
}
K_THREAD_DEFINE(scan_thread, 4096, run, NULL, NULL, NULL, 10, 0, 0);
static int configure(const struct device *dev, kscan_callback_t cb) {
  ARG_UNUSED(dev);
  callback = cb;
  return cb ? 0 : -EINVAL;
}
static int enable(const struct device *dev) {
  ARG_UNUSED(dev);
  atomic_set(&enabled, 1);
  return 0;
}
static int disable(const struct device *dev) {
  ARG_UNUSED(dev);
  atomic_clear(&enabled);
  return 0;
}
static int init(const struct device *dev) {
  if (!device_is_ready(saadc) || !device_is_ready(ports[0]) ||
      !device_is_ready(ports[1]))
    return -ENODEV;
  struct yeti_hal hal = {NULL, gpio, wait_us, sample, unused_report};
  struct yeti_config cfg = {.debounce_frames = 2,
                            .afe_settle_us = 5000,
                            .mux_settle_us = 3,
                            .discharge_us = 10,
                            .charge_us = 5,
                            .acquisition_us = 40};
  for (unsigned r = 0; r < YETI_ROWS; r++)
    for (unsigned c = 0; c < YETI_COLS; c++) {
      cfg.low[r][c] = 1500;
      cfg.high[r][c] = 2000;
    }
  if (yeti_init(&core, &hal, &cfg) || yeti_power(&core, true) || io_fault)
    return -EIO;
  scan_device = dev;
  return 0;
}
static const struct kscan_driver_api api = {.config = configure,
                                            .enable_callback = enable,
                                            .disable_callback = disable};
DEVICE_DT_INST_DEFINE(0, init, NULL, NULL, NULL, POST_KERNEL,
                      CONFIG_KERNEL_INIT_PRIORITY_DEVICE, &api);
