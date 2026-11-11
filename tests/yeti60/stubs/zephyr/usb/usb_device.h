/* Only the legacy status interface, not a USB controller emulation. */
#pragma once
#include <stdint.h>
enum usb_dc_status_code {
  USB_DC_UNKNOWN, USB_DC_DISCONNECTED, USB_DC_CONNECTED,
  USB_DC_CONFIGURED, USB_DC_SUSPEND, USB_DC_RESUME, USB_DC_RESET,
  USB_DC_ERROR, USB_DC_SOF, USB_DC_CLEAR_HALT, USB_DC_SET_HALT,
  USB_DC_INTERFACE
};
typedef void (*usb_dc_status_callback)(enum usb_dc_status_code, const uint8_t *);
int usb_enable(usb_dc_status_callback);
