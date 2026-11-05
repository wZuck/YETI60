/* Trace the production core's GPIO events; costs here are explicit assumptions.
 * SPDX-License-Identifier: MIT */
#include "core.h"
#include "timing.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
static double now, latency;
static void gpio(void *ctx, uint8_t pin, enum yeti_mode mode) {
  (void)ctx;
  const char *names[] = {"HIZ", "LOW", "HIGH", "CLAMP", "RELEASE"};
  printf("%.6f,%s,%u,0\n", now, names[mode], pin);
  now += 0.5;
}
static void wait_us(void *ctx, uint32_t us) { (void)ctx; now += us; }
static int adc(void *ctx, uint8_t ain, uint32_t acquisition) {
  (void)ctx;
  printf("%.6f,ADC_CALL,%u,%u\n", now, ain, acquisition);
  now += latency;
  printf("%.6f,ACQUIRE,%u,%u\n", now, ain, acquisition);
  now += acquisition;
  printf("%.6f,SAMPLE,%u,0\n", now, ain);
  return 0;
}
static bool report(void *ctx, enum yeti_link link, const uint8_t data[8]) {
  (void)ctx; (void)link; (void)data; return true;
}
int main(int argc, char **argv) {
  latency = argc > 1 ? strtod(argv[1], NULL) : 0;
  assert(latency >= 0);
  struct yeti_core core;
  struct yeti_hal hal = {NULL, gpio, wait_us, adc, report};
  struct yeti_config cfg = TEST_CONFIG;
  for (unsigned r = 0; r < YETI_ROWS; r++)
    for (unsigned c = 0; c < YETI_COLS; c++) {
      cfg.low[r][c] = 1500; cfg.high[r][c] = 2000;
    }
  puts("time_us,event,pin,value");
  assert(yeti_init(&core, &hal, &cfg) == 0);
  assert(yeti_power(&core, true) == 0);
  assert(yeti_scan(&core) == 0);
  return 0;
}
