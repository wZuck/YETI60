/* SPDX-License-Identifier: MIT */
#include "usb_policy.h"
#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include <zephyr/kernel.h>
#include <zmk/endpoints.h>
#include <zmk/usb.h>

static enum usb_dc_status_code status;
static bool ready;
static enum zmk_transport preferred = ZMK_TRANSPORT_BLE;
static unsigned preference_writes, gpio_writes;
static int preference_error;
static int queue_error;
static struct k_work *queued;
static enum yeti_mode pins[64];
int k_work_submit(struct k_work *work) {
  if (queue_error)
    return queue_error;
  assert(!queued || queued == work);
  int added = !work->pending;
  work->pending = true;
  queued = work;
  return added;
}
static void drain(void) {
  if (!queued)
    return;
  struct k_work *work = queued;
  queued = NULL;
  work->pending = false;
  work->handler(work);
}
enum usb_dc_status_code zmk_usb_get_status(void) { return status; }
bool zmk_usb_is_hid_ready(void) { return ready; }
enum zmk_transport zmk_endpoint_get_preferred_transport(void) { return preferred; }
int zmk_endpoint_set_preferred_transport(enum zmk_transport value) {
  preference_writes++;
  if (preference_error)
    return preference_error;
  preferred = value;
  return 0;
}
static void gpio(void *ctx, uint8_t pin, enum yeti_mode mode) {
  (void)ctx;
  assert(pin < 64);
  pins[pin] = mode;
  gpio_writes++;
}
static void wait_us(void *ctx, uint32_t us) { (void)ctx; (void)us; }
static int adc(void *ctx, uint8_t ain, uint32_t us) {
  (void)ctx; (void)ain; (void)us;
  return 1000;
}
static bool report(void *ctx, enum yeti_link link, const uint8_t data[8]) {
  (void)ctx; (void)link; (void)data;
  return true;
}
int main(void) {
  struct yeti_core core;
  struct yeti_usb_policy policy = {0};
  struct yeti_hal hal = {NULL, gpio, wait_us, adc, report};
  struct yeti_config cfg = {.debounce_frames = 2, .afe_settle_us = 5000,
      .mux_settle_us = 3, .discharge_us = 10, .charge_us = 5, .acquisition_us = 40};
  for (unsigned r = 0; r < YETI_ROWS; r++)
    for (unsigned c = 0; c < YETI_COLS; c++) {
      cfg.low[r][c] = 1500;
      cfg.high[r][c] = 2000;
    }
  assert(yeti_init(&core, &hal, &cfg) == 0);
  assert(yeti_target_usb_poll(NULL, &core) == -EINVAL);
  status = USB_DC_CONNECTED;
  assert(yeti_target_usb_poll(&policy, &core) == 0);
  assert(pins[PIN_CHG_CE_N] == Y_HIGH && preferred == ZMK_TRANSPORT_BLE);
  assert(pins[PIN_CHG_EN1] == Y_LOW && pins[PIN_CHG_EN2] == Y_LOW);
  status = USB_DC_CONFIGURED; ready = true;
  assert(yeti_target_usb_poll(&policy, &core) == 0);
  assert(queued && preferred == ZMK_TRANSPORT_BLE);
  drain();
  assert(core.link == Y_USB && preferred == ZMK_TRANSPORT_USB);
  assert(pins[PIN_CHG_CE_N] == Y_LOW && pins[PIN_CHG_EN1] == Y_HIGH &&
         pins[PIN_CHG_EN2] == Y_LOW);
  unsigned before = gpio_writes;
  for (unsigned i = 0; i < 1000; i++)
    assert(yeti_target_usb_poll(&policy, &core) == 0);
  assert(preference_writes == 1 && gpio_writes == before);
  preferred = ZMK_TRANSPORT_BLE;
  assert(yeti_target_usb_poll(&policy, &core) == 0);
  drain();
  assert(preferred == ZMK_TRANSPORT_USB && preference_writes == 2);
  assert(pins[PIN_CHG_CE_N] == Y_LOW);
  status = USB_DC_SUSPEND; /* ZMK retains HID-ready across suspend. */
  assert(yeti_target_usb_poll(&policy, &core) == 0);
  assert(pins[PIN_CHG_CE_N] == Y_HIGH && pins[PIN_CHG_EN1] == Y_HIGH &&
         pins[PIN_CHG_EN2] == Y_HIGH);
  status = USB_DC_RESUME;
  assert(yeti_target_usb_poll(&policy, &core) == 0);
  assert(core.link == Y_USB && pins[PIN_CHG_CE_N] == Y_LOW);
  status = USB_DC_RESET; ready = false;
  assert(yeti_target_usb_poll(&policy, &core) == 0);
  assert(pins[PIN_CHG_CE_N] == Y_HIGH && pins[PIN_CHG_EN1] == Y_LOW);
  status = USB_DC_RESUME; /* Resume without accepted configuration is powered only. */
  assert(yeti_target_usb_poll(&policy, &core) == 0);
  assert(pins[PIN_CHG_CE_N] == Y_HIGH);
  status = USB_DC_DISCONNECTED;
  assert(yeti_target_usb_poll(&policy, &core) == 0);
  assert(core.link == Y_NONE && pins[PIN_CHG_CE_N] == Y_HIGH);
  /* The adapter does not force BLE: ZMK owns fallback to a ready BLE profile. */
  assert(preferred == ZMK_TRANSPORT_USB);
  status = USB_DC_CONFIGURED; ready = true;
  preferred = ZMK_TRANSPORT_BLE; preference_error = -EIO;
  assert(yeti_target_usb_poll(&policy, &core) == 0);
  drain();
  assert(preferred == ZMK_TRANSPORT_BLE);
  preference_error = 0;
  assert(yeti_target_usb_poll(&policy, &core) == 0);
  drain();
  assert(preferred == ZMK_TRANSPORT_USB && pins[PIN_CHG_CE_N] == Y_LOW);
  preferred = ZMK_TRANSPORT_BLE; queue_error = -EBUSY;
  assert(yeti_target_usb_poll(&policy, &core) == -EBUSY && !queued);
  queue_error = 0;
  assert(yeti_target_usb_poll(&policy, &core) == 0 && queued);
  status = USB_DC_DISCONNECTED; ready = false;
  drain();
  assert(preferred == ZMK_TRANSPORT_BLE); /* A stale queued attach cannot switch hosts. */
  status = USB_DC_CONFIGURED; ready = true;
  assert(yeti_target_usb_poll(&policy, &core) == 0);
  drain();
  assert(preferred == ZMK_TRANSPORT_USB);
  policy.initialized = false; core.busy = true;
  assert(yeti_target_usb_poll(&policy, &core) != 0 && !policy.initialized);
  puts("USB policy: concurrent configured charging and USB preference; retained BLE override; suspend/resume/reset/detach; no repeated writes; retry failures passed");
  return 0;
}
