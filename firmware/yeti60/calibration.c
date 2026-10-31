/* SPDX-License-Identifier: MIT */
#include "calibration.h"
#include <string.h>

void yeti_cal_reset(struct yeti_cal_stats *s) {
  memset(s, 0, sizeof(*s));
  s->minimum = 4095;
}

bool yeti_cal_add(struct yeti_cal_stats *s, uint16_t sample) {
  if (sample > 4095 || s->count >= YETI_CAL_CAPTURE_SAMPLES)
    return false;
  s->count++;
  s->sum += sample;
  s->sum_squares += (uint64_t)sample * sample;
  if (sample < s->minimum)
    s->minimum = sample;
  if (sample > s->maximum)
    s->maximum = sample;
  return true;
}

static uint32_t ceil_sqrt(uint32_t value) {
  uint32_t low = 0, high = 4096;
  while (low < high) {
    uint32_t mid = low + (high - low) / 2;
    if ((uint64_t)mid * mid < value)
      low = mid + 1;
    else
      high = mid;
  }
  return low;
}

static uint32_t deviation(const struct yeti_cal_stats *s) {
  uint64_t denominator = (uint64_t)s->count * (s->count - 1);
  uint64_t numerator = s->count * s->sum_squares - (uint64_t)s->sum * s->sum;
  return ceil_sqrt((uint32_t)((numerator + denominator - 1) / denominator));
}

bool yeti_cal_thresholds(const struct yeti_cal_stats *released,
                         const struct yeti_cal_stats *pressed,
                         uint16_t *low, uint16_t *high, uint16_t *guard) {
  if (released->count < YETI_CAL_MIN_SAMPLES ||
      pressed->count < YETI_CAL_MIN_SAMPLES ||
      released->count > YETI_CAL_CAPTURE_SAMPLES ||
      pressed->count > YETI_CAL_CAPTURE_SAMPLES ||
      released->maximum >= 4090 || pressed->maximum >= 4090)
    return false;
  uint32_t sr = deviation(released), sp = deviation(pressed);
  uint32_t g = 6 * (sr > sp ? sr : sp);
  if (g < 1)
    g = 1;
  int32_t bottom = (int32_t)released->maximum + (int32_t)g + 1;
  int32_t top = (int32_t)pressed->minimum - (int32_t)g - 1;
  if ((int32_t)pressed->minimum - released->maximum < 32 || top - bottom < 4)
    return false;
  uint16_t lo = (uint16_t)(bottom + (top - bottom) * 35 / 100);
  uint16_t hi = (uint16_t)(bottom + (top - bottom) * 65 / 100);
  if (lo >= hi)
    return false;
  *low = lo;
  *high = hi;
  *guard = (uint16_t)g;
  return true;
}
