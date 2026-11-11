/* SPDX-License-Identifier: MIT */
#include "usb_policy.h"
#include "board_pins.h"
#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/kernel.h>
#include <zephyr/usb/usb_device.h>
#include <zmk/endpoints.h>
#include <zmk/usb.h>

const struct device test_gpio0 = {0}, test_gpio1 = {1};
static usb_dc_status_callback hardware_callback;
static enum zmk_transport preferred = ZMK_TRANSPORT_BLE;
static unsigned preference_writes, gpio_writes, forwarded_events;
static int preference_error, queue_error, enable_error;
static int gpio_fail_after = -1;
static bool gpio_ready = true, expect_configured;
static struct k_work *queue[16];
static unsigned queued;
static int pins[64];
int __wrap_usb_enable(usb_dc_status_callback);
int __real_usb_enable(usb_dc_status_callback callback) {
  hardware_callback = callback;
  return enable_error;
}
int k_work_submit(struct k_work *work) {
  if (queue_error)
    return queue_error;
  if (work->pending)
    return 0;
  assert(queued < 16);
  queue[queued++] = work;
  work->pending = true;
  return 1;
}
static void drain(void) {
  while (queued) {
    struct k_work *work = queue[0];
    memmove(queue, queue + 1, --queued * sizeof(queue[0]));
    work->pending = false;
    work->handler(work);
  }
}
#ifndef YETI_PINNED_USB
static enum usb_dc_status_code status = USB_DC_UNKNOWN;
static bool ready;
enum usb_dc_status_code zmk_usb_get_status(void) { return status; }
bool zmk_usb_is_hid_ready(void) { return ready; }
static void upstream_status(enum usb_dc_status_code value, const uint8_t *params) {
  (void)params;
  status = value;
  if (value == USB_DC_CONFIGURED)
    ready = true;
  if (value == USB_DC_RESET || value == USB_DC_DISCONNECTED || value == USB_DC_CONNECTED)
    ready = false;
}
#else
void usb_status_cb(enum usb_dc_status_code, const uint8_t *);
#define upstream_status usb_status_cb
#endif
static void forward(enum usb_dc_status_code value, const uint8_t *params) {
  /* Immediate pin action must precede ZMK notification, with no poll/drain. */
  assert(pins[PIN_CHG_CE_N] == (expect_configured ? 0 : 1));
  forwarded_events++;
  upstream_status(value, params);
}
enum zmk_transport zmk_endpoint_get_preferred_transport(void) { return preferred; }
int zmk_endpoint_set_preferred_transport(enum zmk_transport value) {
  preference_writes++;
  if (preference_error)
    return preference_error;
  preferred = value;
  return 0;
}
bool device_is_ready(const struct device *dev) { assert(dev == &test_gpio0 || dev == &test_gpio1); return gpio_ready; }
int gpio_pin_set(const struct device *dev, uint32_t pin, int value) {
  assert((dev == &test_gpio0 || dev == &test_gpio1) && pin < 32);
  pin += dev == &test_gpio1 ? 32 : 0;
  if (gpio_fail_after == 0) {
    gpio_fail_after = -1;
    return -EIO;
  }
  if (gpio_fail_after > 0)
    gpio_fail_after--;
  pins[pin] = value;
  gpio_writes++;
  /* Check every intermediate write, not just the final pin combination. */
  assert(!(pins[PIN_CHG_EN1] == 0 && pins[PIN_CHG_EN2] == 1));
  if (!pins[PIN_CHG_CE_N]) {
    assert(expect_configured);
    assert(pins[PIN_CHG_EN1] == 1 && pins[PIN_CHG_EN2] == 0);
  }
  return 0;
}
int gpio_pin_configure(const struct device *dev, uint32_t pin, int flags) {
  return gpio_pin_set(dev, pin, flags == GPIO_OUTPUT_HIGH);
}
static void emit(enum usb_dc_status_code status, int configuration, bool charging) {
  uint8_t value = (uint8_t)configuration;
  expect_configured = charging;
  unsigned before = forwarded_events;
  hardware_callback(status, configuration < 0 ? NULL : &value);
  assert(forwarded_events == before + 1);
  assert(pins[PIN_CHG_CE_N] == (charging ? 0 : 1));
}
int main(int argc, char **argv) {
  pins[PIN_CHG_CE_N] = 1;
  if (argc > 1 && !strcmp(argv[1], "not-ready")) {
    gpio_ready = false;
    assert(yeti_target_usb_init() == -ENODEV);
    puts("USB charger: unavailable GPIO rejects initialization");
    return 0;
  }
  if (argc > 1 && !strncmp(argv[1], "init-fault-", 11)) {
    gpio_fail_after = atoi(argv[1] + 11);
    assert(yeti_target_usb_init() == -EIO);
    assert(pins[PIN_CHG_CE_N] && pins[PIN_CHG_EN1] && pins[PIN_CHG_EN2]);
    puts("USB charger: GPIO initialization failure latches disabled/high-Z");
    return 0;
  }
  assert(yeti_target_usb_init() == 0);
  if (argc > 1 && !strcmp(argv[1], "enable-fault")) {
    enable_error = -EIO;
    assert(__wrap_usb_enable(forward) == -EIO);
    assert(pins[PIN_CHG_CE_N] && pins[PIN_CHG_EN1] && pins[PIN_CHG_EN2]);
    puts("USB charger: stack enable failure latches disabled/high-Z");
    return 0;
  }
  assert(__wrap_usb_enable(forward) == 0 && hardware_callback);
  emit(USB_DC_CONNECTED, -1, false);
  assert(!pins[PIN_CHG_EN1] && !pins[PIN_CHG_EN2]);
  emit(USB_DC_CONFIGURED, 1, true);
  assert(zmk_usb_is_hid_ready());
  unsigned initialized_writes = gpio_writes;
  assert(yeti_target_usb_init() == 0 && gpio_writes == initialized_writes);
  assert(yeti_target_usb_poll() == 0);
  drain();
  assert(preferred == ZMK_TRANSPORT_USB);
  unsigned before = gpio_writes;
  for (unsigned i = 0; i < 1000; i++) {
    emit(USB_DC_SOF, -1, true);
    assert(yeti_target_usb_poll() == 0);
  }
  assert(preference_writes == 1 && gpio_writes == before);
  emit(USB_DC_SUSPEND, -1, false);
  assert(pins[PIN_CHG_EN1] && pins[PIN_CHG_EN2]);
  emit(USB_DC_CLEAR_HALT, -1, false); /* No incidental event lifts suspend. */
  emit(USB_DC_RESUME, -1, true);
  emit(USB_DC_SUSPEND, -1, false);
  emit(USB_DC_RESET, -1, false);
  assert(!pins[PIN_CHG_EN1] && !pins[PIN_CHG_EN2]);
  emit(USB_DC_RESUME, -1, false); /* Reset discarded configuration. */
  emit(USB_DC_CONFIGURED, 1, true);
  emit(USB_DC_CONFIGURED, 0, false);
  assert(!zmk_usb_is_hid_ready() && zmk_usb_get_status() == USB_DC_RESET);
  emit(USB_DC_RESUME, -1, false);
  emit(USB_DC_CONFIGURED, -1, false);
  emit(USB_DC_CONFIGURED, 2, false);
  emit(USB_DC_CONFIGURED, 1, true);
  if (argc > 1 && !strncmp(argv[1], "write-fault-", 12)) {
    emit(USB_DC_SUSPEND, -1, false);
    gpio_fail_after = atoi(argv[1] + 12);
    emit(USB_DC_RESUME, -1, false);
    emit(USB_DC_CONFIGURED, 1, false);
    assert(pins[PIN_CHG_EN1] && pins[PIN_CHG_EN2]);
    puts("USB charger: GPIO write failure stays disabled until reboot");
    return 0;
  }
  preferred = ZMK_TRANSPORT_BLE;
  assert(yeti_target_usb_poll() == 0);
  emit(USB_DC_DISCONNECTED, -1, false);
  drain();
  assert(preferred == ZMK_TRANSPORT_BLE);
  emit(USB_DC_CONFIGURED, 1, true);
  preference_error = -EIO;
  assert(yeti_target_usb_poll() == 0);
  drain(); assert(preferred == ZMK_TRANSPORT_BLE);
  preference_error = 0;
  assert(yeti_target_usb_poll() == 0);
  drain(); assert(preferred == ZMK_TRANSPORT_USB);
  preferred = ZMK_TRANSPORT_BLE;
  queue_error = -EBUSY;
  assert(yeti_target_usb_poll() == -EBUSY);
  emit(USB_DC_SUSPEND, -1, false); /* Queue failure cannot delay charger off. */
  queue_error = 0;
  emit(USB_DC_RESUME, -1, true);
  assert(yeti_target_usb_poll() == 0);
  drain(); assert(preferred == ZMK_TRANSPORT_USB);
  puts("USB events: synchronous charging, USB priority, deconfiguration, suspend/resume/reset/detach, safe intermediate modes, no repeated writes and retry passed");
  return 0;
}
