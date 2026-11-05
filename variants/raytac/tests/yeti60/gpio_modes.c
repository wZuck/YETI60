/* Exercise verbatim target callbacks/init and the actual portable core.
 * Driver/ADC models below implement only their declared host contracts.
 * SPDX-License-Identifier: MIT */
#include "core.h"
#include "gpio_modes.h"
#include "scanner_control.h"
#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>
#include <zephyr/drivers/gpio.h>
#include "zephyr_gpio_constants.h"
#define ARG_UNUSED(value) (void)(value)
struct pin_state { bool output, input, pull, high; };
static struct pin_state states[64];
const struct device test_gpio0 = {0};
static const struct device gpio1 = {1}, adc_device = {2}, scanner_device = {3};
static const struct device *const ports[] = {&test_gpio0, &gpio1};
static const struct device *const saadc = &adc_device;
static const struct device *scan_device;
static struct yeti_core core;
static bool io_fault, pulse_active, ready = true, fail_adc;
static uint32_t pulse_started, fake_cycle;
static unsigned gpio_calls, adc_calls, usb_init_calls;
static int usb_error;
static bool fail_init_gpio;
static uint32_t k_cycle_get_32(void) { return ++fake_cycle; }
bool device_is_ready(const struct device *dev) { (void)dev; return ready; }
static void disconnected(unsigned pin) {
  assert(!states[pin].output && !states[pin].input && !states[pin].pull);
}
static void afe_disconnected(void) {
  for (unsigned i = 0; i < YETI_ROWS; i++) disconnected(yeti_rows[i]);
  for (unsigned i = 0; i < 3; i++) disconnected(yeti_sel[i]);
  for (unsigned i = 0; i < 2; i++) disconnected(yeti_en[i]);
  disconnected(PIN_APLEX_OUT_PIN_0); disconnected(PIN_ADC);
  disconnected(PIN_BAT_ADC);
}
int gpio_pin_configure(const struct device *dev, uint32_t pin, int flags) {
  assert(dev == ports[0] || dev == ports[1]);
  unsigned abs = (dev == ports[1] ? 32 : 0) + pin; assert(abs < 64);
  gpio_calls++;
  if (fail_init_gpio && abs == PIN_APLEX_OUT_PIN_0 && flags == GPIO_OUTPUT_LOW) {
    fail_init_gpio = false;
    return -EIO;
  }
  states[abs] = (struct pin_state){
      .output = (flags & GPIO_OUTPUT) != 0,
      .input = (flags & GPIO_INPUT) != 0,
      .pull = (flags & (GPIO_PULL_UP | GPIO_PULL_DOWN)) != 0,
      .high = (flags & GPIO_OUTPUT_INIT_HIGH) != 0};
  if (abs == PIN_ADC || abs == PIN_BAT_ADC ||
      (abs == PIN_APLEX_OUT_PIN_0 && !states[abs].output))
    disconnected(abs);
  return 0;
}
/* Exact production function bodies are generated into these includes. */
#include "scanner_gpio.inc"
static void wait_us(void *ctx, uint32_t us) { (void)ctx; (void)us; }
static int sample(void *ctx, uint8_t ain, uint32_t acquisition) {
  (void)ctx; assert(acquisition == 40); adc_calls++;
  disconnected(PIN_ADC); disconnected(PIN_BAT_ADC);
  if (fail_adc) return -EIO;
  if (ain == YETI_BAT_AIN) return 2389;
  assert(ain == YETI_ADC_AIN);
  disconnected(PIN_APLEX_OUT_PIN_0);
  assert(states[PIN_AFE_EN].output && states[PIN_AFE_EN].high);
  return 1000;
}
static bool unused_report(void *ctx, enum yeti_link link, const uint8_t report[8]) {
  (void)ctx; (void)link; (void)report; return true;
}
int yeti_target_usb_init(void) { usb_init_calls++; return usb_error; }
#include "scanner_init.inc"
int main(int argc, char **argv) {
  const char *test = argc > 1 ? argv[1] : "normal";
  if (!strcmp(test, "device-missing")) ready = false;
  if (!strcmp(test, "USB-init-failure")) usb_error = -EIO;
  if (!strcmp(test, "GPIO-init-failure")) fail_init_gpio = true;
  int result = init(&scanner_device);
  if (strcmp(test, "normal") && strcmp(test, "ADC-read-failure")) {
    assert(result == (!ready ? -ENODEV : -EIO));
    assert(!scan_device && !core.powered);
    assert(yeti_scan_state() == Y_SCAN_OFFLINE);
    if (!ready) assert(gpio_calls == 0 && usb_init_calls == 0);
    else afe_disconnected();
    assert(!states[PIN_AFE_EN].high);
    printf("Target initialization: %s leaves AFE off, pins disconnected\n", test);
    return 0;
  }
  assert(result == 0 && scan_device == &scanner_device && core.powered);
  assert(yeti_scan_state() == Y_SCAN_RUNNING);
  unsigned before = gpio_calls;
  assert(init(&scanner_device) == -EALREADY && gpio_calls == before);
  if (!strcmp(test, "ADC-read-failure")) {
    fail_adc = true;
    assert(yeti_scan(&core) == -2);
    assert(yeti_power(&core, false) == 0);
    afe_disconnected();
    puts("ADC fault then shutdown: AFE pins have no drive, pulls or digital input buffers");
    return 0;
  }
  assert(yeti_scan(&core) == 0 && adc_calls == 75);
  assert(yeti_afe(&core, false) == 0); afe_disconnected();
  assert(!states[PIN_AFE_EN].high);
  assert(yeti_afe(&core, true) == 0 && yeti_scan(&core) == 0 && adc_calls == 150);
  assert(yeti_power(&core, false) == 0); afe_disconnected();
  uint32_t mv; assert(yeti_battery_mv(&core, &mv) == 0 && adc_calls == 151);
  assert(mv >= 4199 && mv <= 4201); afe_disconnected();
  assert(!states[PIN_BAT_MEAS_EN].high);
  assert(yeti_target_gpio_flags((enum yeti_mode)99) == GPIO_DISCONNECTED);
  puts("GPIO modes: 150 scan samples, idle/wake, off and battery measurement keep analog buffers/drive/pulls disconnected");
  return 0;
}
