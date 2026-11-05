/* Verbatim target shell/worker/fault code with modeled HAL and scheduling.
 * SPDX-License-Identifier: MIT */
#include "core.h"
#include "calibration.h"
#include "scanner_control.h"
#include <zephyr/sys/atomic.h>
#include <assert.h>
#include <errno.h>
#include <setjmp.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#ifndef __unused
#define __unused
#endif
#define ARG_UNUSED(x) (void)(x)
#define BIT(x) (1u << (x))
#define IS_ENABLED(x) (x)
#define K_MSEC(x) (x)
#define CONFIG_YETI60_IDLE_AFTER_MS 30000
#define CONFIG_YETI60_IDLE_SCAN_MS 30
#define CONFIG_YETI60_ACTIVE_SCAN_MS 4
#define CONFIG_YETI60_AFE_IDLE_GATING 1
#define CONFIG_SYS_CLOCK_HW_CYCLES_PER_SEC 32768
#define YETI_CALIBRATION_VERSION 0x12345678u
struct device { unsigned id; };
struct shell { unsigned id; };
typedef void (*kscan_callback_t)(const struct device *, uint32_t, uint32_t, bool);
#include "scanner_globals.inc"
#include "queue_contract.h"
static const struct device test_device = {1};
static struct shell test_shell;
static char output[131072];
static unsigned output_at, shell_errors, shell_acks, saves, polls;
static unsigned adc_calls, sleeps, stop_after, presses, releases, fault_at;
static unsigned inject; /* 1 ADC error, 2 GPIO error at frame end, 3 gate error */
static bool pressed_all, afe_enabled, fail_save, queue_during_fault;
static uint64_t time_ms;
static jmp_buf worker_exit;
typedef ssize_t (*settings_read_cb)(void *, void *, size_t);
static struct yeti_calibration nvs_record;
static unsigned read_calls;
static ssize_t read_result;
static ssize_t read_settings(void *arg, void *data, size_t len) {
  assert(arg==&nvs_record && len==sizeof(nvs_record));
  read_calls++; memcpy(data,&nvs_record,len); return read_result;
}
#include "scanner_load.inc"
static void fixture_record(void) {
  nvs_record.version=YETI_CALIBRATION_VERSION;
  for (unsigned r=0;r<5;r++) for (unsigned c=0;c<15;c++) {
    nvs_record.low[r][c]=1000; nvs_record.high[r][c]=1500;
  }
  nvs_record.crc32=yeti_calibration_checksum(&nvs_record);
  read_result=sizeof(nvs_record);
}
static int load_record(size_t len) {
  return load_calibration("thresholds",len,read_settings,&nvs_record);
}
struct settings_load_arg {
  const char *subtree;
  int (*cb)(const char *, size_t, settings_read_cb, void *, void *);
  void *param;
};
struct settings_handler_static {
  int (*h_set)(const char *, size_t, settings_read_cb, void *);
};
static unsigned unrelated_loaded;
static int unrelated_setting(const char *key, size_t len, settings_read_cb read, void *arg) {
  (void)len; (void)read; (void)arg; assert(!strcmp(key,"keys/0"));
  unrelated_loaded++; return 0;
}
static struct settings_handler_static calibration_handler={load_calibration};
static struct settings_handler_static unrelated_handler={unrelated_setting};
static struct settings_handler_static *settings_parse_and_lookup(const char *name, const char **key) {
  if (!strncmp(name,"yeti60/",7)) { *key=name+7; return &calibration_handler; }
  if (!strncmp(name,"bt/",3)) { *key=name+3; return &unrelated_handler; }
  return NULL;
}
static bool settings_name_steq(const char *name, const char *prefix, const char **key) {
  size_t len=strlen(prefix);
  if (strncmp(name,prefix,len) || (name[len] && name[len]!='/')) return false;
  *key=name+len+(name[len]=='/'); return true;
}
#define LOG_ERR(...) ((void)0)
#define LOG_DBG(...) ((void)0)
#include "settings_dispatch.inc"
#include "zmk_event_types.inc"
static struct layout { const struct device *kscan; } test_layout = {&test_device};
static const struct layout *active_layout = &test_layout;
static struct { unsigned work; } msg_processor;
static struct {
  struct zmk_kscan_event events[CONFIG_ZMK_KSCAN_EVENT_QUEUE_SIZE];
  unsigned count, dropped;
} physical_layouts_kscan_msgq;
#define K_NO_WAIT 0
static int k_msgq_put(void *queue, const void *event, unsigned timeout) {
  assert(queue==&physical_layouts_kscan_msgq && timeout==K_NO_WAIT);
  if (physical_layouts_kscan_msgq.count==CONFIG_ZMK_KSCAN_EVENT_QUEUE_SIZE) {
    physical_layouts_kscan_msgq.dropped++; return -ENOSPC;
  }
  physical_layouts_kscan_msgq.events[physical_layouts_kscan_msgq.count++]=
      *(const struct zmk_kscan_event *)event;
  return 0;
}
static int k_work_submit(void *work) { assert(work==&msg_processor.work); return 0; }
/* Rename only the layout pointer to avoid the scanner active-key bitmap. */
#define active active_layout
#include "zmk_kscan_callback.inc"
#undef active
static void append(const char *fmt, va_list args) {
  int n = vsnprintf(output + output_at, sizeof(output) - output_at, fmt, args);
  assert(n >= 0 && (unsigned)n < sizeof(output) - output_at);
  output_at += n;
}
static void printk(const char *fmt, ...) {
  va_list args; va_start(args, fmt); append(fmt, args); va_end(args);
}
static void shell_print(const struct shell *sh, const char *fmt, ...) {
  (void)sh; shell_acks++;
  va_list args; va_start(args, fmt); append(fmt, args); va_end(args);
}
static void shell_error(const struct shell *sh, const char *fmt, ...) {
  (void)sh; shell_errors++;
  va_list args; va_start(args, fmt); append(fmt, args); va_end(args);
}
static uint64_t k_cyc_to_us_ceil64(uint64_t cycles) {
  return (cycles * 1000000 + 32767) / 32768;
}
static int64_t k_uptime_get(void) { return time_ms; }
static void k_sleep(unsigned ms) {
  time_ms += ms;
  if (++sleeps >= stop_after) longjmp(worker_exit, 1);
}
static int settings_save_one(const char *name, const void *data, size_t size) {
  assert(!strcmp(name, "yeti60/thresholds") && size == sizeof(saved));
  assert(yeti_calibration_valid(data, YETI_CALIBRATION_VERSION));
  saves++; return fail_save ? -EIO : 0;
}
static int yeti_target_usb_poll(void) { polls++; return 0; }
static void events(const struct device *dev, uint32_t row, uint32_t col, bool down) {
  assert(dev == &test_device && row < 5 && col < 15 && (active[row] & BIT(col)));
  if (down) presses++; else releases++;
  zmk_physical_layout_kscan_callback(dev,row,col,down);
}
static void gpio(void *ctx, uint8_t pin, enum yeti_mode mode) {
  (void)ctx;
  if (pin == PIN_AFE_EN) {
    afe_enabled = mode == Y_HIGH;
    if (!afe_enabled && inject == 3) io_fault = true;
  }
}
static void wait_us(void *ctx, uint32_t us) { (void)ctx; (void)us; }
static int sample(void *ctx, uint8_t ain, uint32_t acquisition) {
  (void)ctx; assert(ain == YETI_ADC_AIN && acquisition == 40 && cursor < 75);
  adc_calls++;
  if (fault_at && adc_calls == fault_at) {
    if (queue_during_fault) assert(yeti_scan_submit(3) == 0);
    if (inject == 1) return -EIO;
    if (inject == 2) io_fault = true;
  }
  unsigned row = cursor % 5, col = cursor / 5;
  int value = (active[row] & BIT(col)) &&
              (pressed_all || (calibration_mode == 2 && row == pressed_row && col == pressed_col))
                  ? 2500 : 1000;
  raw[row][col] = value; cursor++;
  return value;
}
static bool report(void *ctx, enum yeti_link link, const uint8_t data[8]) {
  (void)ctx; (void)link; (void)data; return true;
}
#include "scanner_command.inc"
#include "scanner_fault.inc"
#include "scanner_run.inc"
static int request(const char *line) {
  char copy[128]; snprintf(copy, sizeof(copy), "yeti_calibrate %s", line);
  char *argv[8]; unsigned argc = 0;
  for (char *word = strtok(copy, " "); word; word = strtok(NULL, " ")) {
    assert(argc < 8); argv[argc++] = word;
  }
  return command(&test_shell, argc, argv);
}
static void setup(void) {
  struct yeti_hal hal = {NULL, gpio, wait_us, sample, report};
  struct yeti_config cfg = {.debounce_frames=2, .afe_settle_us=5000,
      .mux_settle_us=3, .discharge_us=10, .charge_us=5, .acquisition_us=40};
  for (unsigned r=0; r<5; r++) for (unsigned c=0; c<15; c++) {
    cfg.low[r][c]=1500; cfg.high[r][c]=2000;
  }
  assert(yeti_init(&core, &hal, &cfg) == 0 && yeti_power(&core, true) == 0);
  scan_device=&test_device; callback=events;
  assert(yeti_scan_ready()); atomic_set(&enabled, 1); calibrated=true;
}
static void frames(unsigned count) {
  sleeps=0; stop_after=count;
  if (!setjmp(worker_exit)) run(NULL, NULL, NULL);
}
static void parser(void) {
  unsigned count=0;
  const char *bad[]={"press", "press x 1", "press 0 x", "press -1 0",
      "press 5 0", "press 0 15", "press 0 1z", "status extra", "unknown"};
  for (unsigned i=0; i<sizeof(bad)/sizeof(bad[0]); i++) assert(request(bad[i]) == -EINVAL);
  for (unsigned r=0; r<5; r++) for (unsigned c=0; c<15; c++) {
    char cmd[32]; snprintf(cmd, sizeof(cmd), "press %u %u", r, c);
    if (active[r] & BIT(c)) {
      assert(request(cmd)==0 && yeti_scan_take()==(int)(2|((r*15+c)<<8))); count++;
    } else assert(request(cmd)==-EINVAL);
  }
  assert(count==60);
}
int main(int argc, char **argv) {
  assert(argc==2); const char *test=argv[1];
  if (!strcmp(test,"offline")) {
    assert(request("release")==-ENODEV && request("status")==-ENODEV);
    assert(shell_errors==2 && shell_acks==0 && yeti_scan_take()==0);
    assert(strstr(output,"initialization has not succeeded")); frames(2);
    assert(!adc_calls && !polls && !saves);
  } else {
    setup();
    if (!strcmp(test,"parser")) parser();
    else if (!strcmp(test,"queue-burst")) {
      for (unsigned down=0;down<2;down++)
        for (unsigned r=0;r<5;r++) for (unsigned c=0;c<15;c++)
          if (active[r]&BIT(c)) events(&test_device,r,c,down==0);
      assert(physical_layouts_kscan_msgq.count==120);
      for (unsigned i=0;i<120;i++)
        assert(physical_layouts_kscan_msgq.events[i].state==
            (i<60?ZMK_KSCAN_EVENT_STATE_PRESSED:ZMK_KSCAN_EVENT_STATE_RELEASED));
    }
    else if (!strcmp(test,"queue")) {
      assert(request("release")==0 && request("save")==-EBUSY);
      assert(yeti_scan_take()==1 && yeti_scan_take()==0);
      assert(request("timing")==0 && yeti_scan_take()==5);
      assert(shell_errors==1 && strstr(output,"command pending"));
      assert(yeti_scan_submit(0)==-EINVAL && yeti_scan_submit(6)==-EINVAL);
      assert(yeti_scan_submit(3|256)==-EINVAL && yeti_scan_submit(2|(75<<8))==-EINVAL);
    } else if (!strcmp(test,"fault-race")) {
      assert(request("save")==0 && yeti_scan_fault() && yeti_scan_take()==-EIO);
      assert(!yeti_scan_fault() && !yeti_scan_ready());
      assert(yeti_scan_state()==Y_SCAN_FAULT);
      assert(request("release")==-EIO && request("press 0 0")==-EIO && request("save")==-EIO);
      assert(request("status")==0 && yeti_scan_take()==4);
      assert(request("timing")==0 && yeti_scan_take()==5);
      assert(strstr(output,"diagnose hardware and reset"));
    } else if (!strcmp(test,"cleanup")) {
      uint16_t previous[5]; memcpy(previous, active, sizeof(previous));
      calibration_mode=2; calibration_started=true; idle_scan=true; afe_asleep=true;
      fault_shutdown(-EIO,previous);
      assert(!core.powered && !afe_enabled && !calibrated && !calibration_mode);
      assert(!calibration_started && !idle_scan && !afe_asleep && releases==60);
      for (unsigned r=0;r<5;r++) assert(!previous[r] && !core.matrix[r]);
      unsigned logged=output_at; fault_shutdown(-EIO,previous);
      assert(releases==60 && output_at==logged && !saves);
    } else if (!strcmp(test,"worker-ADC") || !strcmp(test,"worker-GPIO")) {
      pressed_all=true; inject=!strcmp(test,"worker-ADC")?1:2;
      /* Frame two establishes sixty held keys. Fault during frame three. */
      fault_at=inject==1?151:225; queue_during_fault=true;
      frames(3);
      assert(presses==60 && releases==60 && !core.powered && !afe_enabled);
      assert(!calibrated && yeti_scan_state()==Y_SCAN_FAULT && !saves);
      unsigned reads=adc_calls; frames(1);
      assert(adc_calls==reads && strstr(output,"queued calibration rejected"));
      assert(request("status")==0); frames(1);
      assert(strstr(output,"scanner_fault=1") && !saves && adc_calls==reads);
      assert(request("timing")==0); frames(1); assert(adc_calls==reads);
    } else if (!strcmp(test,"load-reject")) {
      fixture_record();
      assert(load_calibration("unknown",sizeof(nvs_record),read_settings,&nvs_record)==-ENOENT);
      size_t lengths[]={0,1,303,304,307,309,4096};
      for (unsigned i=0;i<sizeof(lengths)/sizeof(lengths[0]);i++) {
        unsigned before=read_calls;
        assert(load_record(lengths[i])==-EINVAL && read_calls==before);
      }
      read_result=-EIO; assert(load_record(sizeof(nvs_record))==-EINVAL);
      read_result=sizeof(nvs_record)-1; assert(load_record(sizeof(nvs_record))==-EINVAL);
      read_result=sizeof(nvs_record);
      nvs_record.low[0][0]^=1; assert(load_record(sizeof(nvs_record))==-EINVAL);
      fixture_record(); nvs_record.version^=1;
      nvs_record.crc32=yeti_calibration_checksum(&nvs_record);
      assert(load_record(sizeof(nvs_record))==-EINVAL);
      fixture_record(); nvs_record.high[0][0]=4096;
      nvs_record.crc32=yeti_calibration_checksum(&nvs_record);
      assert(load_record(sizeof(nvs_record))==-EINVAL);
      assert(!atomic_get(&calibration_loaded));
    } else if (!strcmp(test,"settings-dispatch")) {
      fixture_record(); nvs_record.low[0][0]^=1;
      assert(settings_call_set_handler("yeti60/thresholds",sizeof(nvs_record),read_settings,&nvs_record,NULL)==0);
      assert(!atomic_get(&calibration_loaded));
      assert(settings_call_set_handler("bt/keys/0",0,NULL,NULL,NULL)==0);
      assert(unrelated_loaded==1);
    } else if (!strcmp(test,"worker-load")) {
      fixture_record(); calibrated=false;
      assert(load_record(sizeof(nvs_record))==0 && atomic_get(&calibration_loaded));
      struct yeti_calibration before=saved;
      nvs_record.low[0][0]^=1;
      assert(load_record(sizeof(nvs_record))==-EINVAL);
      assert(!memcmp(&saved,&before,sizeof(saved)) && atomic_get(&calibration_loaded));
      frames(1);
      assert(calibrated && !atomic_get(&calibration_loaded) && !saves);
      for (unsigned r=0;r<5;r++) for (unsigned c=0;c<15;c++)
        assert(core.cfg.low[r][c]==1000 && core.cfg.high[r][c]==1500);
      assert(!presses && !releases);
    } else if (!strcmp(test,"worker-GPIO-capture")) {
      inject=2; fault_at=75; queue_during_fault=true;
      assert(request("release")==0); frames(1);
      assert(yeti_scan_state()==Y_SCAN_FAULT && !core.powered);
      for (unsigned r=0;r<5;r++) for (unsigned c=0;c<15;c++)
        assert(released[r][c].count==0);
      frames(1); assert(!saves && strstr(output,"queued calibration rejected"));
    } else if (!strcmp(test,"worker-disabled-GPIO")) {
      atomic_clear(&enabled); inject=3; frames(1);
      assert(yeti_scan_state()==Y_SCAN_FAULT && !core.powered && !calibrated);
      assert(!adc_calls && !saves);
    } else if (!strcmp(test,"worker-calibration")) {
      fixture_record(); saved=nvs_record;
      assert(request("save")==0); frames(1); assert(!saves);
      assert(request("release")==0); frames(128);
      assert(calibration_started && !calibration_mode && released[0][0].count==128);
      assert(request("save")==0); frames(1); assert(!saves);
      unsigned keys=0;
      for (unsigned r=0;r<5;r++) for (unsigned c=0;c<15;c++) if (active[r]&BIT(c)) {
        char cmd[32]; snprintf(cmd,sizeof(cmd),"press %u %u",r,c);
        assert(request(cmd)==0); frames(128);
        assert(!calibration_mode && pressed[r][c].count==128); keys++;
      }
      assert(keys==60 && request("save")==0); fail_save=true; frames(1);
      assert(saves==1 && !calibrated);
      assert(!memcmp(&saved,&nvs_record,sizeof(saved)));
      fail_save=false; assert(request("save")==0); frames(1);
      assert(saves==2 && calibrated && saved.version==YETI_CALIBRATION_VERSION);
      assert(yeti_calibration_valid(&saved,YETI_CALIBRATION_VERSION));
      assert(!presses && !releases && yeti_scan_state()==Y_SCAN_RUNNING);
    } else assert(!"unknown scenario");
  }
  assert(!physical_layouts_kscan_msgq.dropped);
  printf("Scanner control: %s passed\n",test); return 0;
}
