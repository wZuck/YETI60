/* Host GPIO double; ARM firmware uses the actual nrfx driver. */
#pragma once
#include <stdbool.h>
#include <stdint.h>
struct device { int unused; };
extern const struct device test_gpio0;
#define DT_NODELABEL(name) name
#define DEVICE_DT_GET(node) (&test_gpio0)
typedef uint32_t gpio_flags_t;
#define GPIO_INPUT (1U << 16)
#define GPIO_OUTPUT (1U << 17)
#define GPIO_DISCONNECTED 0
#define GPIO_OUTPUT_INIT_LOW (1U << 18)
#define GPIO_OUTPUT_INIT_HIGH (1U << 19)
#define GPIO_OUTPUT_LOW (GPIO_OUTPUT | GPIO_OUTPUT_INIT_LOW)
#define GPIO_OUTPUT_HIGH (GPIO_OUTPUT | GPIO_OUTPUT_INIT_HIGH)
#define GPIO_PULL_UP (1 << 4)
#define GPIO_PULL_DOWN (1 << 5)
bool device_is_ready(const struct device *);
int gpio_pin_configure(const struct device *, uint32_t, int);
int gpio_pin_set(const struct device *, uint32_t, int);
