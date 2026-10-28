/* SPDX-License-Identifier: MIT */
#define DT_DRV_COMPAT yeti_ec60
#include "core.h"
#include <string.h>
#include <zephyr/device.h>
#include <zephyr/drivers/adc.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/drivers/kscan.h>
#include <zephyr/kernel.h>
#include <zephyr/settings/settings.h>
#include <zephyr/shell/shell.h>
#include <zmk/usb.h>

static struct yeti_core core;
static const struct device *scan_device;
static kscan_callback_t callback;
static atomic_t enabled;
static bool io_fault;
static bool calibrated;
static atomic_t calibration_command;
static atomic_t calibration_loaded;
static uint16_t raw[5][15], released[5][15], pressed[5][15];
static unsigned cursor;
static int calibration_mode;
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
  ARG_UNUSED(argc);
  int mode = !strcmp(argv[1], "release") ? 1
             : !strcmp(argv[1], "press") ? 2
             : !strcmp(argv[1], "save")  ? 3
                                         : 0;
  if (!mode)
    return -EINVAL;
  atomic_set(&calibration_command, mode);
  shell_print(shell,
              "Queued calibration step %d; release samples all keys up, press "
              "samples each key fully down, save validates range.",
              mode);
  return 0;
}
#if defined(CONFIG_SHELL)
SHELL_CMD_ARG_REGISTER(yeti_calibrate, NULL, "release | press | save", command,
                       2, 0);
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
    if (action == 1) {
      calibrated = false;
      calibration_mode = 1;
      memset(released, 0xff, sizeof(released));
      memset(pressed, 0, sizeof(pressed));
    } else if (action == 2 && calibration_mode == 1)
      calibration_mode = 2;
    else if (action == 3 && calibration_mode == 2) {
      bool valid = true;
      for (unsigned r = 0; r < 5; r++)
        for (unsigned c = 0; c < 15; c++) {
          /* Unused layout positions are not required to be pressed. */
          static const uint16_t active[5] = {0x7fff, 0x3fff, 0x2fff, 0x1ffd,
                                             0x4646};
          int span = (int)pressed[r][c] - released[r][c];
          if ((active[r] & BIT(c)) && (span < 32 || pressed[r][c] >= 4090))
            valid = false;
          saved.low[r][c] =
              span >= 32 ? released[r][c] + span * 35 / 100 : 4094;
          saved.high[r][c] =
              span >= 32 ? released[r][c] + span * 60 / 100 : 4095;
        }
      if (valid) {
        saved.version = YETI_CALIBRATION_VERSION;
        int rc = settings_save_one("yeti60/thresholds", &saved, sizeof(saved));
        if (!rc) {
          memcpy(core.cfg.low, saved.low, sizeof(saved.low));
          memcpy(core.cfg.high, saved.high, sizeof(saved.high));
          memset(core.matrix, 0, sizeof(core.matrix));
          memset(core.count, 0, sizeof(core.count));
          calibrated = true;
        }
      }
      printk("YETI60 calibration %s\n",
             calibrated
                 ? "saved"
                 : "rejected; check every key and retry release/press/save");
      calibration_mode = 0;
    }
    enum usb_dc_status_code usb = zmk_usb_get_status();
    if (usb != old) {
      enum yeti_usb state = usb == USB_DC_CONFIGURED     ? Y_USB_CONFIGURED
                            : usb == USB_DC_SUSPEND      ? Y_USB_SUSPENDED
                            : usb == USB_DC_DISCONNECTED ? Y_USB_OFF
                                                         : Y_USB_POWERED;
      /* Keep USB100 even after enumeration: enough for selected low-current
       * pack. */
      yeti_connections(&core, state, 100, false);
      old = usb;
    }
    if (atomic_get(&enabled)) {
      cursor = 0;
      int err = yeti_scan(&core);
      if (!err && calibration_mode) {
        for (unsigned r = 0; r < 5; r++)
          for (unsigned c = 0; c < 15; c++) {
            if (calibration_mode == 1 && raw[r][c] < released[r][c])
              released[r][c] = raw[r][c];
            if (calibration_mode == 2 && raw[r][c] > pressed[r][c])
              pressed[r][c] = raw[r][c];
          }
      }
      if (!calibrated)
        memset(core.matrix, 0, sizeof(core.matrix));
      for (unsigned row = 0; row < YETI_ROWS; row++) {
        uint16_t changed = previous[row] ^ core.matrix[row];
        for (unsigned col = 0; col < YETI_COLS; col++)
          if ((changed & BIT(col)) && callback)
            callback(scan_device, row, col, (core.matrix[row] & BIT(col)) != 0);
        previous[row] = core.matrix[row];
      }
      if (err || io_fault) {
        yeti_power(&core, false);
        k_sleep(K_MSEC(100));
      }
    }
    k_sleep(K_MSEC(4));
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
