/* SPDX-License-Identifier: MIT */
#pragma once
#include "core.h"

struct yeti_usb_policy {
  bool initialized;
  enum yeti_usb previous;
};

/* Called by the scanner owner. ZMK continues to own actual HID delivery. */
int yeti_target_usb_poll(struct yeti_usb_policy *, struct yeti_core *);
