/* Host-only interfaces for the pinned, unmodified ZMK tap-dance source. */
#pragma once
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define IS_ENABLED(x) 0
#define DT_HAS_COMPAT_STATUS_OKAY(x) 1
#define DT_INST_FOREACH_STATUS_OKAY(x)
#define CONFIG_ZMK_BEHAVIOR_TAP_DANCE_MAX_HELD 4
#define LOG_MODULE_DECLARE(...)
#define LOG_DBG(...)
#define LOG_ERR(...)
#define ZMK_LISTENER(...)
#define ZMK_SUBSCRIPTION(...)
#define K_MSEC(x) (x)
#define ZMK_EV_EVENT_BUBBLE 0
#define ZMK_BEHAVIOR_OPAQUE 1
#define CONTAINER_OF(ptr, type, field) ((type *)((char *)(ptr)-offsetof(type,field)))
struct device { const void *config; };
struct k_work { void (*handler)(struct k_work *); };
struct k_work_delayable { struct k_work work; int64_t due; bool pending; };
struct zmk_behavior_binding { const char *behavior_dev; uint32_t param1,param2; };
struct zmk_behavior_binding_event { uint32_t position; int64_t timestamp; };
struct zmk_position_state_changed { uint32_t position; bool state; int64_t timestamp; };
typedef struct zmk_position_state_changed zmk_event_t;
struct behavior_driver_api {
  int (*binding_pressed)(struct zmk_behavior_binding *,struct zmk_behavior_binding_event);
  int (*binding_released)(struct zmk_behavior_binding *,struct zmk_behavior_binding_event);
};
static int64_t now_ms;
static int64_t k_uptime_get(void) { return now_ms; }
static void k_work_init_delayable(struct k_work_delayable *w,void (*fn)(struct k_work *)) {
  w->work.handler=fn;w->pending=false;
}
static int k_work_cancel_delayable(struct k_work_delayable *w) { w->pending=false;return 0; }
static int k_work_schedule(struct k_work_delayable *w,int64_t delay) { w->due=now_ms+delay;w->pending=true;return 1; }
static struct k_work_delayable *k_work_delayable_from_work(struct k_work *w) { return (struct k_work_delayable *)w; }
static struct zmk_position_state_changed *as_zmk_position_state_changed(const zmk_event_t *e) {
  return (struct zmk_position_state_changed *)e;
}
static const struct device *zmk_behavior_get_binding(const char *name);
static int zmk_behavior_invoke_binding(struct zmk_behavior_binding *,struct zmk_behavior_binding_event,bool);
