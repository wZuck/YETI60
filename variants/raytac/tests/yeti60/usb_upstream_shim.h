/* Native harness for the complete, unmodified pinned ZMK app/src/usb.c. */
#pragma once
#include <errno.h>
#include <zephyr/kernel.h>
#include <zmk/usb.h>
#define LOG_MODULE_DECLARE(...)
#define LOG_DBG(...)
#define LOG_ERR(...)
#define CONFIG_ZMK_LOG_LEVEL 0
#define IS_ENABLED(option) 0
#define SYS_INIT(...)
#define APPLICATION 0
#define CONFIG_ZMK_USB_INIT_PRIORITY 50
struct zmk_usb_conn_state_changed { enum zmk_usb_conn_state conn_state; };
static inline int raise_zmk_usb_conn_state_changed(struct zmk_usb_conn_state_changed event) {
  (void)event; return 0;
}
