#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#define PAL_MODE_INPUT_ANALOG 0
void fake_gpio(uint32_t pin, bool value);
#define writePin(pin, value) fake_gpio((pin), !!(value))
#define writePinHigh(pin) fake_gpio((pin), true)
#define writePinLow(pin) fake_gpio((pin), false)
#define setPinOutput(pin) ((void)(pin))
#define setPinOutputOpenDrain(pin) ((void)(pin))
#define palSetLineMode(pin, mode) ((void)(pin), (void)(mode))
