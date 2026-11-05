/* Host GPIO double; ARM firmware uses the actual nrfx driver. */
#pragma once
#include <stdbool.h>
#include <stdint.h>
struct device { int unused; };
extern const struct device test_gpio0;
#define DT_NODELABEL(name) name
#define DEVICE_DT_GET(node) (&test_gpio0)
#define GPIO_OUTPUT_LOW 0
#define GPIO_OUTPUT_HIGH 1
bool device_is_ready(const struct device *);
int gpio_pin_configure(const struct device *, uint32_t, int);
int gpio_pin_set(const struct device *, uint32_t, int);
