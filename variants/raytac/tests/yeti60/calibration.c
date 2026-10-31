/* SPDX-License-Identifier: MIT */
#include "calibration.h"
#include <assert.h>
#include <stdio.h>

static void fill(struct yeti_cal_stats *s, uint16_t baseline, unsigned count) {
  yeti_cal_reset(s);
  for (unsigned i = 0; i < count; i++)
    assert(yeti_cal_add(s, (uint16_t)(baseline + i % 3)));
}

int main(void) {
  struct yeti_cal_stats r, p;
  uint16_t low = 0, high = 0, guard = 0;
  fill(&r, 1000, 128);
  fill(&p, 1500, 128);
  assert(yeti_cal_thresholds(&r, &p, &low, &high, &guard));
  assert(guard >= 6 && r.maximum + guard < low && low < high &&
         high < p.minimum - guard);
  assert(!yeti_cal_add(&p, 4000)); /* Completed capture cannot keep optimistic peaks. */
  fill(&p, 1500, 63);
  assert(!yeti_cal_thresholds(&r, &p, &low, &high, &guard));
  fill(&p, 1001, 128);
  assert(!yeti_cal_thresholds(&r, &p, &low, &high, &guard));
  /* Old min(released)/max(pressed) would accept these overlapping populations. */
  fill(&p, 1000, 127);
  assert(yeti_cal_add(&p, 2000));
  assert(!yeti_cal_thresholds(&r, &p, &low, &high, &guard));
  fill(&p, 1500, 127);
  assert(yeti_cal_add(&p, 4095));
  assert(!yeti_cal_thresholds(&r, &p, &low, &high, &guard));
  fill(&r, 1000, 127);
  assert(yeti_cal_add(&r, 2000));
  fill(&p, 1800, 128);
  assert(!yeti_cal_thresholds(&r, &p, &low, &high, &guard));
  /* Exercise full ADC range and integer variance without overflow. */
  yeti_cal_reset(&r);
  for (unsigned i = 0; i < 128; i++)
    assert(yeti_cal_add(&r, i % 2 ? 4089 : 0));
  assert(!yeti_cal_thresholds(&r, &p, &low, &high, &guard));
  assert(!yeti_cal_add(&r, 4096));
  puts("Calibration: guarded worst-case populations accepted; insufficient, overlapping, noisy, saturated and out-of-range samples rejected (ASan/UBSan).");
  return 0;
}
