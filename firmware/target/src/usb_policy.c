/* SPDX-License-Identifier: MIT */
#include "usb_policy.h"
#include <errno.h>
#include <zephyr/kernel.h>
#include <zmk/endpoints.h>
#include <zmk/usb.h>

static void select_usb(struct k_work *work) {
  (void)work;
  /* Endpoint changes clear ZMK reports. Serialize that mutation with ZMK's
   * USB notifications and key events on the system workqueue, never here
   * on the separate EC scanner thread. Recheck after queued detach/suspend. */
  if (zmk_usb_get_status() != USB_DC_SUSPEND && zmk_usb_is_hid_ready() &&
      zmk_endpoint_get_preferred_transport() != ZMK_TRANSPORT_USB)
    (void)zmk_endpoint_set_preferred_transport(ZMK_TRANSPORT_USB);
}
K_WORK_DEFINE(yeti_usb_priority_work, select_usb);

int yeti_target_usb_poll(struct yeti_usb_policy *policy, struct yeti_core *core) {
  if (!policy || !core)
    return -EINVAL;
  enum usb_dc_status_code usb = zmk_usb_get_status();
  enum yeti_usb state = usb == USB_DC_SUSPEND ? Y_USB_SUSPENDED
                        : zmk_usb_is_hid_ready() ? Y_USB_CONFIGURED
                        : (usb == USB_DC_DISCONNECTED || usb == USB_DC_UNKNOWN)
                            ? Y_USB_OFF : Y_USB_POWERED;
  if (!policy->initialized || state != policy->previous) {
    /* Legacy bMaxPower units are 2 mA. Charging and HID are concurrent once
     * configured; suspend/reset cannot enable charging. */
    int err = yeti_connections(core, state, CONFIG_USB_MAX_POWER * 2, false);
    if (err)
      return err;
    policy->previous = state;
    policy->initialized = true;
  }
  /* A retained BLE preference must not override a ready wired connection.
   * On detach ZMK automatically falls back to the active BLE profile. Its
   * endpoint API owns handover and old-host releases. No NVS write is made
   * when the preference is already USB. Retry a rejected update next poll. */
  if (state == Y_USB_CONFIGURED &&
      zmk_endpoint_get_preferred_transport() != ZMK_TRANSPORT_USB) {
    int err = k_work_submit(&yeti_usb_priority_work);
    return err < 0 ? err : 0;
  }
  return 0;
}
