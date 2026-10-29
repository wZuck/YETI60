/* YETI60 portable nRF52840 control core. SPDX-License-Identifier: MIT */
#include "core.h"
#include <stddef.h>
#include <string.h>
static void io(struct yeti_core *s, uint8_t p, enum yeti_mode m) {
  s->hal.gpio(s->hal.ctx, p, m);
}
static void wait(struct yeti_core *s, uint32_t us) {
  s->hal.wait_us(s->hal.ctx, us);
}
static void rows_low(struct yeti_core *s) {
  for (unsigned r = 0; r < YETI_ROWS; r++)
    io(s, yeti_rows[r], Y_LOW);
}
static void inhibit(struct yeti_core *s) {
  io(s, yeti_en[0], Y_HIGH);
  io(s, yeti_en[1], Y_HIGH);
}
static void high_z(struct yeti_core *s) {
  for (unsigned r = 0; r < YETI_ROWS; r++)
    io(s, yeti_rows[r], Y_HIZ);
  for (unsigned i = 0; i < 3; i++)
    io(s, yeti_sel[i], Y_HIZ);
  for (unsigned i = 0; i < 2; i++)
    io(s, yeti_en[i], Y_HIZ);
  io(s, PIN_APLEX_OUT_PIN_0, Y_HIZ);
  io(s, PIN_ADC, Y_HIZ);
}
static void hid(struct yeti_core *s) {
  uint8_t release[8] = {0};
  for (enum yeti_link link = Y_USB; link <= Y_BLE; link++) {
    if (!(s->pending_release & (1u << link)))
      continue;
    if (s->hal.report(s->hal.ctx, link, release))
      s->pending_release &= (uint8_t)~(1u << link);
  }
  if (s->link != Y_NONE && (s->pending_release & (1u << s->link))) {
    s->dirty = true;
    return;
  }
  uint8_t report[8] = {0};
  unsigned n = 0;
  for (unsigned r = 0; r < YETI_ROWS; r++)
    for (unsigned c = 0; c < YETI_COLS; c++) {
      if (!(s->matrix[r] & (1u << c)))
        continue;
      uint8_t u = s->cfg.usage[r][c];
      if (u >= 0xe0 && u <= 0xe7)
        report[0] |= (uint8_t)(1u << (u - 0xe0));
      else if (u) {
        bool duplicate = false;
        for (unsigned j = 2; j < 8; j++)
          duplicate |= report[j] == u;
        if (!duplicate) {
          if (n < 6)
            report[2 + n] = u;
          n++;
        }
      }
    }
  if (n > 6)
    memset(report + 2, 1, 6); /* USB boot protocol ErrorRollOver. */
  if (s->link != Y_NONE && (s->dirty || memcmp(report, s->last_report, 8))) {
    if (s->hal.report(s->hal.ctx, s->link, report)) {
      memcpy(s->last_report, report, 8);
      s->dirty = false;
    } else
      s->dirty = true;
  }
}
int yeti_init(struct yeti_core *s, const struct yeti_hal *hal,
              const struct yeti_config *cfg) {
  if (!s || !hal || !cfg || !hal->gpio || !hal->wait_us || !hal->adc ||
      !hal->report)
    return -1;
  if (!cfg->debounce_frames || !cfg->afe_settle_us || !cfg->mux_settle_us ||
      !cfg->discharge_us || !cfg->charge_us || cfg->acquisition_us < 3)
    return -1;
  for (unsigned r = 0; r < YETI_ROWS; r++)
    for (unsigned c = 0; c < YETI_COLS; c++)
      if (cfg->low[r][c] >= cfg->high[r][c] || cfg->high[r][c] > 4095)
        return -1;
  /* Inputs may refer to the same instance during a powered-off reinit. */
  struct yeti_hal hal_copy = *hal;
  struct yeti_config cfg_copy = *cfg;
  memset(s, 0, sizeof(*s));
  s->hal = hal_copy;
  s->cfg = cfg_copy;
  s->initialized = true;
  s->busy = true;
  high_z(s);
  io(s, PIN_AFE_EN, Y_LOW);
  io(s, PIN_BAT_MEAS_EN, Y_LOW);
  io(s, PIN_BAT_ADC, Y_HIZ);
  io(s, PIN_CHG_CE_N, Y_HIGH);
  io(s, PIN_CHG_EN1, Y_LOW);
  io(s, PIN_CHG_EN2, Y_LOW);
  s->busy = false;
  return 0;
}
static void afe_up(struct yeti_core *s) {
  high_z(s);
  io(s, PIN_AFE_EN, Y_HIGH);
  wait(s, s->cfg.afe_settle_us);
  rows_low(s);
  for (unsigned i = 0; i < 3; i++)
    io(s, yeti_sel[i], Y_LOW);
  inhibit(s);
  io(s, PIN_APLEX_OUT_PIN_0, Y_OD_LOW);
}
static void afe_down(struct yeti_core *s) {
  rows_low(s);
  inhibit(s);
  io(s, PIN_APLEX_OUT_PIN_0, Y_OD_LOW);
  high_z(s);
  io(s, PIN_AFE_EN, Y_LOW);
}
int yeti_power(struct yeti_core *s, bool on) {
  if (!s || !s->initialized || s->busy)
    return -1;
  if (on == s->powered && (!on || s->afe_on))
    return 0;
  s->busy = true;
  if (on) {
    afe_up(s);
    s->afe_on = true;
    s->powered = true;
  } else {
    afe_down(s);
    s->afe_on = false;
    s->powered = false;
    memset(s->matrix, 0, sizeof(s->matrix));
    memset(s->count, 0, sizeof(s->count));
    s->dirty = true;
    hid(s);
  }
  s->busy = false;
  return 0;
}
int yeti_afe(struct yeti_core *s, bool on) {
  if (!s || !s->initialized || s->busy || !s->powered)
    return -1;
  if (on == s->afe_on)
    return 0;
  s->busy = true;
  if (on)
    afe_up(s);
  else
    afe_down(s);
  s->afe_on = on;
  s->busy = false;
  return 0;
}
int yeti_scan(struct yeti_core *s) {
  if (!s || !s->initialized || !s->powered || !s->afe_on || s->busy)
    return -1;
  s->busy = true;
  uint16_t samples[YETI_ROWS][YETI_COLS];
  for (unsigned c = 0; c < YETI_COLS; c++) {
    inhibit(s);
    for (unsigned i = 0; i < 3; i++)
      io(s, yeti_sel[i], (yeti_channels[c] & (1u << i)) ? Y_HIGH : Y_LOW);
    wait(s, s->cfg.mux_settle_us);
    io(s, yeti_en[c / 8], Y_LOW);
    for (unsigned r = 0; r < YETI_ROWS; r++) {
      rows_low(s);
      io(s, PIN_APLEX_OUT_PIN_0, Y_OD_LOW);
      wait(s, s->cfg.discharge_us);
      io(s, yeti_rows[r], Y_HIGH);
      io(s, PIN_APLEX_OUT_PIN_0, Y_OD_RELEASE);
      wait(s, s->cfg.charge_us);
      int v = s->hal.adc(s->hal.ctx, YETI_ADC_AIN, s->cfg.acquisition_us);
      io(s, yeti_rows[r], Y_LOW);
      io(s, PIN_APLEX_OUT_PIN_0, Y_OD_LOW);
      if (v < 0 || v > 4095) {
        rows_low(s);
        inhibit(s);
        memset(s->matrix, 0, sizeof(s->matrix));
        memset(s->count, 0, sizeof(s->count));
        s->dirty = true;
        hid(s);
        s->busy = false;
        return -2;
      }
      samples[r][c] = (uint16_t)v;
    }
  }
  inhibit(s);
  rows_low(s);
  io(s, PIN_APLEX_OUT_PIN_0, Y_OD_LOW);
  for (unsigned r = 0; r < YETI_ROWS; r++)
    for (unsigned c = 0; c < YETI_COLS; c++) {
      bool current = (s->matrix[r] & (1u << c)) != 0;
      bool desired = current;
      if (samples[r][c] > s->cfg.high[r][c])
        desired = true;
      else if (samples[r][c] < s->cfg.low[r][c])
        desired = false;
      if (desired == current)
        s->count[r][c] = 0;
      else if (++s->count[r][c] >= s->cfg.debounce_frames) {
        s->matrix[r] ^= (uint16_t)(1u << c);
        s->count[r][c] = 0;
      }
    }
  hid(s);
  s->busy = false;
  return 0;
}
int yeti_battery_mv(struct yeti_core *s, uint32_t *mv) {
  if (!s || !s->initialized || s->busy || !mv)
    return -1;
  s->busy = true;
  io(s, PIN_BAT_MEAS_EN, Y_HIGH);
  wait(s, 50000);
  int v = s->hal.adc(s->hal.ctx, YETI_BAT_AIN, s->cfg.acquisition_us);
  io(s, PIN_BAT_MEAS_EN, Y_LOW);
  s->busy = false;
  if (v < 0 || v > 4095)
    return -2;
  *mv = ((uint32_t)v * 7200u + 2047u) / 4095u;
  return 0; /* 0.6 V / gain 1/6, 1M:1M. */
}
int yeti_connections(struct yeti_core *s, enum yeti_usb usb, unsigned host_ma,
                     bool ble) {
  if (!s || !s->initialized || s->busy ||
      (usb < Y_USB_OFF || usb > Y_USB_SUSPENDED))
    return -1;
  s->busy = true;
  bool suspend = usb == Y_USB_SUSPENDED,
       large = usb == Y_USB_CONFIGURED && host_ma >= 500;
  /* Disable charging while changing the USB current-limit mode. */
  io(s, PIN_CHG_CE_N, Y_HIGH);
  io(s, PIN_CHG_EN1, (suspend || large) ? Y_HIGH : Y_LOW);
  io(s, PIN_CHG_EN2, suspend ? Y_HIGH : Y_LOW);
  if (usb == Y_USB_CONFIGURED)
    io(s, PIN_CHG_CE_N, Y_LOW);
  enum yeti_link next =
      usb == Y_USB_CONFIGURED ? Y_USB : (ble ? Y_BLE : Y_NONE);
  if (next != s->link) {
    if (s->link != Y_NONE)
      s->pending_release |= (uint8_t)(1u << s->link);
    s->link = next;
    s->dirty = true;
    memset(s->last_report, 0, 8);
  }
  hid(s);
  s->busy = false;
  return 0;
}
