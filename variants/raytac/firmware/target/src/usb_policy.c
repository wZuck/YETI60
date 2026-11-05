/* SPDX-License-Identifier: MIT */
#include "usb_policy.h"
#include "board_pins.h"
#include <errno.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/kernel.h>
#include <zephyr/usb/usb_device.h>
#include <zmk/endpoints.h>
#include <zmk/usb.h>

BUILD_ASSERT(PIN_CHG_EN1 < 32 && PIN_CHG_EN2 < 32 && PIN_CHG_CE_N < 32);
BUILD_ASSERT(CONFIG_USB_MAX_POWER == 250, "Charger USB500 requires a 500 mA descriptor");
static const struct device *const port = DEVICE_DT_GET(DT_NODELABEL(gpio0));
static struct k_spinlock lock;
static usb_dc_status_callback upstream;
static bool initialized, fault, configured, suspended, applied;
static int previous_mode;

/* Called with lock held. Keep CE disabled during every mode change. Passing
 * through EN1=1 first avoids the unintended EN1=0/EN2=1 (external ILIM) mode
 * even when moving from high impedance to USB100. */
static void apply_charger(void) {
  int mode = fault || suspended ? 2 : configured ? 1 : 0;
  if (!initialized || (applied && mode == previous_mode))
    return;
  int err = gpio_pin_set(port, PIN_CHG_CE_N, 1) ||
            gpio_pin_set(port, PIN_CHG_EN1, 1) ||
            gpio_pin_set(port, PIN_CHG_EN2, mode == 2) ||
            gpio_pin_set(port, PIN_CHG_EN1, mode != 0);
  if (!err && mode == 1)
    err = gpio_pin_set(port, PIN_CHG_CE_N, 0);
  if (err) {
    /* A failed GPIO operation cannot authorize charging. Best effort only;
     * electrical pin failure cannot be repaired or proved safe in software. */
    fault = true;
    (void)gpio_pin_set(port, PIN_CHG_CE_N, 1);
    (void)gpio_pin_set(port, PIN_CHG_EN1, 1);
    (void)gpio_pin_set(port, PIN_CHG_EN2, 1);
    mode = 2;
  }
  previous_mode = mode;
  applied = true;
}

int yeti_target_usb_init(void) {
  if (!device_is_ready(port))
    return -ENODEV;
  k_spinlock_key_t key = k_spin_lock(&lock);
  if (initialized) {
    bool failed = fault;
    k_spin_unlock(&lock, key);
    return failed ? -EIO : 0;
  }
  int err = gpio_pin_configure(port, PIN_CHG_CE_N, GPIO_OUTPUT_HIGH);
  err |= gpio_pin_configure(port, PIN_CHG_EN1, GPIO_OUTPUT_LOW);
  err |= gpio_pin_configure(port, PIN_CHG_EN2, GPIO_OUTPUT_LOW);
  initialized = true;
  fault |= err != 0;
  apply_charger();
  bool failed = fault;
  k_spin_unlock(&lock, key);
  return failed ? -EIO : 0;
}

/* The pinned Zephyr stack supplies a configuration byte, including zero for
 * SET_CONFIGURATION(0). ZMK's callback ignores this byte. Normalize a zero or
 * missing byte to RESET for ZMK while keeping the charger unconfigured. */
static void usb_status(enum usb_dc_status_code status, const uint8_t *params) {
  enum usb_dc_status_code forwarded = status;
  k_spinlock_key_t key = k_spin_lock(&lock);
  switch (status) {
  case USB_DC_CONFIGURED:
    configured = params && *params == 1;
    suspended = false;
    if (!configured)
      forwarded = USB_DC_RESET;
    break;
  case USB_DC_SUSPEND:
    suspended = true;
    break;
  case USB_DC_RESUME:
    suspended = false;
    break;
  case USB_DC_CONNECTED:
  case USB_DC_DISCONNECTED:
  case USB_DC_RESET:
  case USB_DC_UNKNOWN:
  case USB_DC_ERROR:
    configured = false;
    suspended = status == USB_DC_ERROR;
    break;
  default:
    break; /* SOF, interface and halt events do not change power permission. */
  }
  apply_charger();
  k_spin_unlock(&lock, key);
  if (upstream)
    upstream(forwarded, params);
}

/* Linker wrapping preserves the original USB stack and ZMK callback without
 * patching either dependency or replacing the controller's internal callback.
 * Charger writes complete before the asynchronous ZMK notification is queued. */
extern int __real_usb_enable(usb_dc_status_callback callback);
int __wrap_usb_enable(usb_dc_status_callback callback) {
  k_spinlock_key_t key = k_spin_lock(&lock);
  bool ready = initialized && !fault;
  k_spin_unlock(&lock, key);
  if (!ready)
    return -ENODEV;
  upstream = callback;
  int err = __real_usb_enable(usb_status);
  if (err) {
    k_spinlock_key_t key = k_spin_lock(&lock);
    fault = true;
    apply_charger();
    k_spin_unlock(&lock, key);
  }
  return err;
}

static bool wired_ready(void) {
  k_spinlock_key_t key = k_spin_lock(&lock);
  bool ready = initialized && !fault && configured && !suspended;
  k_spin_unlock(&lock, key);
  return ready && zmk_usb_is_hid_ready();
}

static void select_usb(struct k_work *work) {
  (void)work;
  /* Endpoint changes clear ZMK reports: serialize with its system workqueue. */
  if (wired_ready() &&
      zmk_endpoint_get_preferred_transport() != ZMK_TRANSPORT_USB)
    (void)zmk_endpoint_set_preferred_transport(ZMK_TRANSPORT_USB);
}
K_WORK_DEFINE(yeti_usb_priority_work, select_usb);

int yeti_target_usb_poll(void) {
  /* This retry concerns HID preference only. Charging never waits for a scan,
   * calibration capture, console print, NVS write or queued endpoint change. */
  if (wired_ready() &&
      zmk_endpoint_get_preferred_transport() != ZMK_TRANSPORT_USB) {
    int err = k_work_submit(&yeti_usb_priority_work);
    return err < 0 ? err : 0;
  }
  return 0;
}
