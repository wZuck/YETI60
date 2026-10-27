/* Run the actual production C scanner with mocked GPIO and ADC under ASan/UBSan. */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "config.h"
#include SCANNER_SOURCE
#include MATRIX_SOURCE

static bool gpio[32];
static unsigned adc_count;
static uint16_t adc_value;
static bool inspect_mux;

void fake_gpio(uint32_t pin, bool value) {
    assert(pin < sizeof(gpio) / sizeof(gpio[0]));
    gpio[pin] = value;
}

uint16_t adc_read(adc_mux mux) {
    assert(mux == ANALOG_PORT);
    if (inspect_mux) {
        unsigned col = adc_count / MATRIX_ROWS;
        assert(col < MATRIX_COLS);
        unsigned selected = gpio[B6] | (gpio[B5] << 1) | (gpio[B4] << 2);
        assert(selected == col_channels[col % 8]);
        assert(gpio[col < 8 ? APLEX_EN_PIN_0 : APLEX_EN_PIN_1] == false);
        assert(gpio[col < 8 ? APLEX_EN_PIN_1 : APLEX_EN_PIN_0] == true);
    }
    adc_count++;
    return adc_value;
}

static ecsm_config_t valid_config(void) {
    ecsm_config_t cfg = {0};
    for (unsigned r = 0; r < MATRIX_ROWS; r++) {
        for (unsigned c = 0; c < MATRIX_COLS; c++) {
            cfg.low_threshold_matrix[r][c] = 350;
            cfg.high_threshold_matrix[r][c] = 450;
        }
    }
    return cfg;
}

int main(int argc, char **argv) {
    assert(argc == 2);
    ecsm_config_t cfg = valid_config();
    matrix_row_t keys[MATRIX_ROWS] = {0};
    if (!strcmp(argv[1], "row-bounds")) {
        clear_all_row_pins();
        puts("row bounds passed");
        return 0;
    }
    assert(ecsm_init(&cfg) == 0);
    if (!strcmp(argv[1], "scan-bounds")) {
        ecsm_matrix_scan(keys);
        assert(adc_count == MATRIX_ROWS * MATRIX_COLS);
        puts("matrix bounds passed");
        return 0;
    }
    inspect_mux = true;
    for (unsigned r = 0; r < MATRIX_ROWS; r++) {
        for (unsigned c = 0; c < MATRIX_COLS; c++) {
            assert(low_threshold[r][c] < high_threshold[r][c]);
        }
    }
    /* Equal thresholds do not switch; the hysteresis band preserves state. */
    const uint16_t samples[] = {350, 450, 451, 400, 350, 349, 400};
    const bool pressed[] = {false, false, true, true, true, false, false};
    for (unsigned i = 0; i < sizeof(samples) / sizeof(samples[0]); i++) {
        adc_value = samples[i];
        adc_count = 0;
        ecsm_matrix_scan(keys);
        assert(adc_count == MATRIX_ROWS * MATRIX_COLS);
        for (unsigned r = 0; r < MATRIX_ROWS; r++) {
            assert(keys[r] == (pressed[i] ? ((1u << MATRIX_COLS) - 1) : 0));
        }
    }
    cfg.low_threshold_matrix[0][0] = cfg.high_threshold_matrix[0][0];
    assert(ecsm_init(&cfg) == -1);
    keys[0] = 1;
    adc_count = 0;
    assert(ecsm_matrix_scan(keys));
    assert(keys[0] == 0 && adc_count == 0);
    assert(ecsm_init(NULL) == -1);
    adc_value = 0;
    matrix_init_custom();
    assert(ecsm_matrix_scan(keys) == false);
    puts("scanner: 75 channels, mux mapping, hysteresis and invalid-config handling passed");
    return 0;
}
