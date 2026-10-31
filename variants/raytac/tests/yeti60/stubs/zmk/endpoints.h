/* Host test doubles, not a radio/USB stack implementation. */
#pragma once
enum zmk_transport { ZMK_TRANSPORT_NONE, ZMK_TRANSPORT_USB, ZMK_TRANSPORT_BLE };
enum zmk_transport zmk_endpoint_get_preferred_transport(void);
int zmk_endpoint_set_preferred_transport(enum zmk_transport);
