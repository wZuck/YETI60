/* SPDX-License-Identifier: MIT */
#include "calibration.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

static void fill(struct yeti_cal_stats *s, uint16_t baseline, unsigned count) {
  yeti_cal_reset(s);
  for (unsigned i = 0; i < count; i++)
    assert(yeti_cal_add(s, (uint16_t)(baseline + i % 3)));
}

int main(int argc, char **argv) {
  _Static_assert(sizeof(struct yeti_calibration) == 308, "NVS layout changed");
  if (argc == 2 && !strcmp(argv[1], "--records")) {
    struct yeti_calibration value;
    while (fread(&value, 1, sizeof(value), stdin) == sizeof(value))
      printf("%08x %u\n", (unsigned)yeti_calibration_checksum(&value),
             yeti_calibration_valid(&value, value.version) ? 1u : 0u);
    assert(feof(stdin)); return 0;
  }
  (void)argv;
  struct yeti_calibration record = {.version = 0x12345678};
  for (unsigned row = 0; row < YETI_ROWS; row++)
    for (unsigned col = 0; col < YETI_COLS; col++) {
      record.low[row][col] = 1000;
      record.high[row][col] = 1500;
    }
  record.crc32 = yeti_calibration_checksum(&record);
  assert(record.crc32 == EXPECTED_RECORD_CRC);
  assert(yeti_calibration_valid(&record, 0x12345678));
  assert(!yeti_calibration_valid(&record, 0x12345679));
  assert(!yeti_calibration_valid(NULL, 0x12345678));
  for (unsigned row = 0; row < YETI_ROWS; row++)
    for (unsigned col = 0; col < YETI_COLS; col++) {
      record.high[row][col] = 4096;
      record.crc32 = yeti_calibration_checksum(&record);
      assert(!yeti_calibration_valid(&record, record.version));
      record.high[row][col] = record.low[row][col];
      record.crc32 = yeti_calibration_checksum(&record);
      assert(!yeti_calibration_valid(&record, record.version));
      record.high[row][col] = 1500;
      record.crc32 = yeti_calibration_checksum(&record);
    }
  assert(yeti_calibration_valid(&record, record.version));
  uint8_t *bytes = (uint8_t *)&record;
  for (unsigned bit = 0; bit < sizeof(record) * 8; bit++) {
    bytes[bit / 8] ^= (uint8_t)(1u << (bit % 8));
    assert(!yeti_calibration_valid(&record, 0x12345678));
    bytes[bit / 8] ^= (uint8_t)(1u << (bit % 8));
  }
  for (unsigned byte = 0; byte < sizeof(record); byte++) {
    bytes[byte] ^= 255;
    assert(!yeti_calibration_valid(&record, 0x12345678));
    bytes[byte] ^= 255;
  }
  for (unsigned bit = 0; bit <= sizeof(record) * 8 - 32; bit++) {
    for (unsigned i = bit; i < bit + 32; i++) bytes[i / 8] ^= (uint8_t)(1u << (i % 8));
    assert(!yeti_calibration_valid(&record, 0x12345678));
    for (unsigned i = bit; i < bit + 32; i++) bytes[i / 8] ^= (uint8_t)(1u << (i % 8));
  }
  puts("Calibration storage: 2464 single-bit flips, 308 byte inversions and 2433 sliding 32-bit bursts rejected.");
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
