/* SPDX-License-Identifier: MIT */
#pragma once
/* Initialize before ZMK enables USB. The USB callback owns charger pins after
 * this call; scanner polling only requests the preferred HID transport. */
int yeti_target_usb_init(void);
int yeti_target_usb_poll(void);
