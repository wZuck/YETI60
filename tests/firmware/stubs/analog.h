#pragma once
#include <stdint.h>
typedef uint8_t adc_mux;
#define pinToMux(pin) ((adc_mux)(pin))
uint16_t adc_read(adc_mux mux);
