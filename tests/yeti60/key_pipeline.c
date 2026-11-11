/* SPDX-License-Identifier: MIT
 * Pinned ZMK functions plus modeled queue/event/behavior/endpoint interfaces.
 * This fixture does not execute a radio, USB controller, scanner or RTOS. */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include "config.inc"
#define IS_ENABLED(x) (x)
#define BIT(x) (1u << (x))
#define WRITE_BIT(x,n,v) ((v) ? ((x) |= BIT(n)) : ((x) &= ~BIT(n)))
#define LOG_MODULE_DECLARE(...)
#define LOG_DBG(...)
#define LOG_WRN(...)
#define LOG_ERR(...)
#define __packed __attribute__((packed))
#define ZMK_HID_REPORT_ID_KEYBOARD 1
#define ZMK_HID_REPORT_ID_CONSUMER 2
#define ZMK_HID_CONSUMER_MAX_USAGE 0xfff
#include <zmk/keys.h>
#include <dt-bindings/zmk/keys.h>
#include <dt-bindings/zmk/bt.h>
#include "hid_structs.inc"
#include "hid.c"
#include "keycode_event.inc"
typedef uint8_t zmk_keymap_layer_id_t;
typedef uint32_t zmk_keymap_layers_state_t;
#define ZMK_KEYMAP_LEN 60
#define ZMK_KEYMAP_LAYERS_LEN 2
#define ZMK_KEYMAP_LAYER_ID_INVAL 255
#define LAYER_ID_TO_INDEX(x) (x)
#define LAYER_INDEX_TO_ID(x) (x)
#define ASSERT_LAYER_VAL(layer,ret) if ((layer)>=2) return (ret);
#define CONFIG_ZMK_SPLIT 0
#define INDEX_OFFSET 1
#define K_NO_WAIT 0
#define ZMK_POSITION_STATE_CHANGE_SOURCE_LOCAL 0
#define ZMK_KSCAN_EVENT_STATE_PRESSED 0
#define ZMK_KSCAN_EVENT_STATE_RELEASED 1
struct zmk_behavior_binding { const char *behavior_dev; uint32_t param1,param2; };
struct zmk_behavior_binding_event { uint8_t layer; uint32_t position; int64_t timestamp; };
struct behavior_mo_config { bool locking; };
struct device { const void *config; };
struct k_work { unsigned id; };
struct zmk_matrix_transform;
typedef const struct zmk_matrix_transform *zmk_matrix_transform_t;
struct layout { const struct device *kscan; zmk_matrix_transform_t matrix_transform; };
struct zmk_kscan_event { uint32_t row,column; uint8_t state; };
struct zmk_position_state_changed { uint8_t source; bool state; uint32_t position; int64_t timestamp; };
static zmk_keymap_layers_state_t _zmk_keymap_layer_locks, _zmk_keymap_layer_state;
static zmk_keymap_layer_id_t _zmk_keymap_layer_default;
static uint32_t zmk_keymap_active_behavior_layer[60];
#include "bindings.inc"
static const struct behavior_mo_config mo_cfg={false};
static const struct device test_device={&mo_cfg};
static struct layout test_layout;
static struct layout *active=&test_layout;
static struct { struct k_work work; } msg_processor;
static struct {
    struct zmk_kscan_event events[CONFIG_ZMK_KSCAN_EVENT_QUEUE_SIZE];
    unsigned read,write;
} physical_layouts_kscan_msgq;
static uint32_t identity_map[60];
static unsigned sent_reports,position_events,control_presses,profile_commands;
static unsigned last_profile,unknown_commands;
static int64_t now_ms;
static struct zmk_hid_keyboard_report_body sent_body;
static int zmk_behavior_invoke_binding(const struct zmk_behavior_binding *,struct zmk_behavior_binding_event,bool);
static int raise_zmk_position_state_changed(struct zmk_position_state_changed);
static int zmk_endpoint_send_report(uint16_t usage_page) {
    assert(usage_page==HID_USAGE_KEY);
    sent_reports++;
    sent_body=zmk_hid_get_keyboard_report()->body;
    return 0;
}
static int64_t k_uptime_get(void) { return now_ms; }
static int k_work_submit(struct k_work *work) { assert(work==&msg_processor.work); return 0; }
static int k_msgq_put(void *q,const void *ev,unsigned timeout) {
    assert(q==&physical_layouts_kscan_msgq && timeout==K_NO_WAIT);
    assert(physical_layouts_kscan_msgq.write<CONFIG_ZMK_KSCAN_EVENT_QUEUE_SIZE);
    physical_layouts_kscan_msgq.events[physical_layouts_kscan_msgq.write++]=*(const struct zmk_kscan_event *)ev;
    return 0;
}
static int k_msgq_get(void *q,void *ev,unsigned timeout) {
    assert(q==&physical_layouts_kscan_msgq && timeout==K_NO_WAIT);
    if(physical_layouts_kscan_msgq.read==physical_layouts_kscan_msgq.write) return -EAGAIN;
    *(struct zmk_kscan_event *)ev=physical_layouts_kscan_msgq.events[physical_layouts_kscan_msgq.read++];
    return 0;
}
static int raise_layer_state_changed(uint8_t layer,bool state,bool locking) {
    (void)state;(void)locking;assert(layer<2);return 0;
}
static const struct device *zmk_behavior_get_binding(const char *name) {
    assert(!strcmp(name,"zmk,behavior-momentary-layer"));return &test_device;
}
static int zmk_physical_layouts_get_selected_to_stock_position_map(const uint32_t **map) {
    *map=identity_map;return 60;
}
/* Actual BT command decoder calls these modeled BLE boundaries. */
static int zmk_ble_prof_select(uint8_t profile) { profile_commands++;last_profile=profile;return 0; }
static void zmk_ble_clear_bonds(void) { unknown_commands++; }
static int zmk_ble_prof_next(void) { unknown_commands++;return 0; }
static int zmk_ble_prof_prev(void) { unknown_commands++;return 0; }
static void zmk_ble_clear_all_bonds(void) { unknown_commands++; }
static int zmk_ble_prof_disconnect(uint8_t profile) { (void)profile;unknown_commands++;return 0; }
#define ZMK_BEHAVIOR_OPAQUE 0
#include "functions.inc"
static int raise_zmk_keycode_state_changed(struct zmk_keycode_state_changed ev) {
    return ev.state?hid_listener_keycode_pressed(&ev):hid_listener_keycode_released(&ev);
}
static int zmk_behavior_invoke_binding(const struct zmk_behavior_binding *binding,
                                      struct zmk_behavior_binding_event event,bool down) {
    struct zmk_behavior_binding copy=*binding;
    if(!strcmp(binding->behavior_dev,"zmk,behavior-key-press"))
        return down?on_keymap_binding_pressed(&copy,event):on_keymap_binding_released(&copy,event);
    if(!strcmp(binding->behavior_dev,"zmk,behavior-momentary-layer"))
        return down?mo_keymap_binding_pressed(&copy,event):mo_keymap_binding_released(&copy,event);
    if(!strcmp(binding->behavior_dev,"zmk,behavior-transparent")) return 1;
    if(!strcmp(binding->behavior_dev,"zmk,behavior-bluetooth")) {
        return down?bt_keymap_binding_pressed(&copy,event):bt_keymap_binding_released(&copy,event);
    }
    if(!strcmp(binding->behavior_dev,"zmk,behavior-tap-dance")) {
        if(down) control_presses++;
        return 0; /* Actual dance timing is tested separately. */
    }
    unknown_commands++; return -ENOTSUP;
}
static int raise_zmk_position_state_changed(struct zmk_position_state_changed ev) {
    position_events++;
    assert(ev.position<60);
    assert(zmk_keymap_position_state_changed(ev.source,ev.position,ev.state,ev.timestamp)==0);
    return 0;
}
static void edge_cell(unsigned row,unsigned col,bool down,bool drain) {
    now_ms++;
    zmk_physical_layout_kscan_callback(&test_device,row,col,down);
    if(drain) {
        zmk_physical_layouts_kscan_process_msgq(&msg_processor.work);
        assert(physical_layouts_kscan_msgq.read==physical_layouts_kscan_msgq.write);
        physical_layouts_kscan_msgq.read=physical_layouts_kscan_msgq.write=0;
    }
}
static void edge(unsigned position,bool down) {
    assert(position<60);
    edge_cell(matrix_cells[position]>>8,matrix_cells[position]&255,down,true);
}
static bool zero_report(void) {
    struct zmk_hid_keyboard_report_body zero={0};
    return !memcmp(&zmk_hid_get_keyboard_report()->body,&zero,sizeof(zero));
}
static void assert_usage(uint32_t encoded,bool down) {
    assert(ZMK_HID_USAGE_PAGE(encoded)==HID_USAGE_KEY);
    assert(zmk_hid_is_pressed(encoded)==down);
    assert(!memcmp(&sent_body,&zmk_hid_get_keyboard_report()->body,sizeof(sent_body)));
}
static const uint32_t expected_fn[60]={
    [0]=GRAVE,[1]=F1,[2]=F2,[3]=F3,[4]=F4,[5]=F5,[6]=F6,
    [7]=F7,[8]=F8,[9]=F9,[10]=F10,[11]=F11,[12]=F12,[14]=DELETE,
    [36]=LEFT,[37]=DOWN,[38]=UP,[39]=RIGHT};
int main(int argc,char **argv) {
    assert(argc==2);
    for(unsigned i=0;i<60;i++) identity_map[i]=i;
    static const struct zmk_matrix_transform matrix={lookup,75,5,15,0,0};
    test_layout=(struct layout){&test_device,&matrix};
    unsigned checked=0;
    if(!strcmp(argv[1],"base")) {
        for(unsigned i=0;i<60;i++) {
            assert(zmk_matrix_transform_row_column_to_position(&matrix,matrix_cells[i]>>8,matrix_cells[i]&255)==(int)i);
            edge(i,true);
            if(expected_base[i]) assert_usage(expected_base[i],true);
            else assert(i==54 && _zmk_keymap_layer_state==BIT(1) && zero_report());
            edge(i,false);assert(zero_report() && !_zmk_keymap_layer_state);checked++;
        }
        assert(sent_reports==118);
    } else if(!strcmp(argv[1],"fn")) {
        for(unsigned i=0;i<60;i++) {
            if(i==54) continue;
            edge(54,true);edge(i,true);
            if(i>=16 && i<=20) {
                assert(last_profile==i-16 && zero_report());
            } else if(i==28) assert(control_presses==1 && zero_report());
            else assert_usage(expected_fn[i]?expected_fn[i]:expected_base[i],true);
            edge(i,false);edge(54,false);
            assert(zero_report() && !_zmk_keymap_layer_state);checked++;
        }
        assert(profile_commands==5 && control_presses==1);
    } else if(!strcmp(argv[1],"layer-release-order")) {
        /* Base key stays a base release after Fn becomes active. */
        edge(1,true);assert_usage(N1,true);edge(54,true);edge(1,false);
        assert(zero_report());edge(54,false);
        /* Fn key stays an Fn release after Fn itself is released. */
        edge(54,true);edge(1,true);assert_usage(F1,true);edge(54,false);edge(1,false);
        assert(zero_report() && !_zmk_keymap_layer_state);checked=2;
    } else if(!strcmp(argv[1],"rollover")) {
        for(unsigned i=1;i<=6;i++) { edge(i,true);assert_usage(expected_base[i],true); }
        edge(7,true);assert(!zmk_hid_is_pressed(expected_base[7]));
        edge(1,false);
        /* The held seventh key is not automatically reinserted by HKRO. */
        assert(!zmk_hid_is_pressed(expected_base[7]));
        edge(7,false);edge(7,true);assert_usage(expected_base[7],true);
        for(unsigned i=2;i<=7;i++) edge(i,false);
        assert(zero_report());checked=7;
    } else if(!strcmp(argv[1],"unused")) {
        for(unsigned row=0;row<5;row++) for(unsigned col=0;col<15;col++) if(!lookup[row*15+col]) {
            edge_cell(row,col,true,true);edge_cell(row,col,false,true);checked++;
        }
        assert(checked==15 && !position_events && !sent_reports && zero_report());
    } else if(!strcmp(argv[1],"all-release")) {
        for(unsigned i=0;i<60;i++) edge(i,true);
        for(unsigned i=60;i>0;i--) edge(i-1,false);
        assert(zero_report() && !_zmk_keymap_layer_state);
        for(unsigned i=0;i<8;i++) assert(explicit_modifier_counts[i]==0);
        assert(position_events==120);checked=60;
    } else assert(!"Unknown case");
    assert(!unknown_commands);
    printf("{\"checked\":%u,\"position_events\":%u,\"report_submissions\":%u,\"profile_commands\":%u,\"tap_dance_boundary_presses\":%u}\n",
           checked,position_events,sent_reports,profile_commands,control_presses);
    return 0;
}
