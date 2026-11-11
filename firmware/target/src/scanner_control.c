/* SPDX-License-Identifier: MIT */
#include "scanner_control.h"
#include <errno.h>
#include <zephyr/sys/atomic.h>

static atomic_t phase;
static atomic_t pending;

enum yeti_scan_state yeti_scan_state(void) { return atomic_get(&phase); }
bool yeti_scan_ready(void) {
  return atomic_cas(&phase, Y_SCAN_OFFLINE, Y_SCAN_RUNNING);
}
bool yeti_scan_fault(void) {
  return atomic_cas(&phase, Y_SCAN_RUNNING, Y_SCAN_FAULT);
}
static bool mutation(unsigned action) { return (action & 255) <= 3; }
int yeti_scan_submit(unsigned action) {
  unsigned opcode = action & 255;
  if (opcode < 1 || opcode > 5 || (opcode != 2 && action != opcode) ||
      (opcode == 2 && (action >> 8) >= 75))
    return -EINVAL;
  enum yeti_scan_state state = yeti_scan_state();
  if (state == Y_SCAN_OFFLINE)
    return -ENODEV;
  if (state == Y_SCAN_FAULT && mutation(action))
    return -EIO;
  return atomic_cas(&pending, 0, action) ? 0 : -EBUSY;
}
int yeti_scan_take(void) {
  unsigned action = atomic_set(&pending, 0);
  if (action && mutation(action) && yeti_scan_state() != Y_SCAN_RUNNING)
    return -EIO;
  return action;
}
