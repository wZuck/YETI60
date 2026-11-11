/* SPDX-License-Identifier: MIT */
#pragma once
#include "core.h"
#include <zephyr/drivers/gpio.h>

/* These pins are never read through GPIO->IN. Disconnecting the digital input
 * buffer leaves the analog pad/SAADC path available without pulls or drive. */
static inline gpio_flags_t yeti_target_gpio_flags(enum yeti_mode mode) {
  switch (mode) {
  case Y_HIZ:
    return GPIO_DISCONNECTED;
  case Y_OD_RELEASE:
    return GPIO_DISCONNECTED;
  case Y_HIGH:
    return GPIO_OUTPUT_HIGH;
  case Y_LOW:
  case Y_OD_LOW:
    return GPIO_OUTPUT_LOW;
  default:
    return GPIO_DISCONNECTED;
  }
}
