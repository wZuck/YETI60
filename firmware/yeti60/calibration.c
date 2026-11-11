/* SPDX-License-Identifier: MIT */
#include "calibration.h"
#include <stddef.h>
#include <string.h>

_Static_assert(sizeof(struct yeti_calibration) == 308, "NVS record size changed");
_Static_assert(offsetof(struct yeti_calibration, crc32) == 304,
               "NVS CRC offset changed");
static uint32_t crc_byte(uint32_t crc, uint8_t value) {
  crc ^= value;
  for (unsigned bit = 0; bit < 8; bit++)
    crc = (crc >> 1) ^ ((crc & 1u) ? 0xedb88320u : 0u);
  return crc;
}
uint32_t yeti_calibration_checksum(const struct yeti_calibration *value) {
  uint32_t crc = 0xffffffffu;
  for (unsigned byte = 0; byte < 4; byte++)
    crc = crc_byte(crc, (uint8_t)(value->version >> (byte * 8)));
  for (unsigned kind = 0; kind < 2; kind++)
    for (unsigned r = 0; r < YETI_ROWS; r++)
      for (unsigned c = 0; c < YETI_COLS; c++) {
        uint16_t threshold = kind ? value->high[r][c] : value->low[r][c];
        crc = crc_byte(crc, (uint8_t)threshold);
        crc = crc_byte(crc, (uint8_t)(threshold >> 8));
      }
  return crc ^ 0xffffffffu;
}
bool yeti_calibration_valid(const struct yeti_calibration *value,
                            uint32_t expected) {
  if (!value || value->version != expected ||
      value->crc32 != yeti_calibration_checksum(value))
    return false;
  for (unsigned r = 0; r < YETI_ROWS; r++)
    for (unsigned c = 0; c < YETI_COLS; c++)
      if (value->low[r][c] >= value->high[r][c] || value->high[r][c] > 4095)
        return false;
  return true;
}

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
