/* Host test doubles; the ARM build uses the pinned Zephyr/ZMK headers. */
#pragma once
#include <stdbool.h>
enum usb_dc_status_code {
  USB_DC_UNKNOWN, USB_DC_DISCONNECTED, USB_DC_CONNECTED,
  USB_DC_CONFIGURED, USB_DC_SUSPEND, USB_DC_RESUME, USB_DC_RESET
};
enum usb_dc_status_code zmk_usb_get_status(void);
bool zmk_usb_is_hid_ready(void);
