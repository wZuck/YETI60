/* SPDX-License-Identifier: MIT */
#pragma once
#include <stdbool.h>
#include <stdint.h>

#define YETI_CAL_MIN_SAMPLES 64u
#define YETI_CAL_CAPTURE_SAMPLES 128u
struct yeti_cal_stats {
  uint32_t count, sum;
  uint64_t sum_squares;
  uint16_t minimum, maximum;
};
void yeti_cal_reset(struct yeti_cal_stats *);
bool yeti_cal_add(struct yeti_cal_stats *, uint16_t sample);
/* Worst-case observed bounds plus a conservative six-standard-deviation guard.
 * This is a calibration screen, not an error-rate or RF-immunity guarantee. */
bool yeti_cal_thresholds(const struct yeti_cal_stats *released,
                         const struct yeti_cal_stats *pressed,
                         uint16_t *low, uint16_t *high, uint16_t *guard);
