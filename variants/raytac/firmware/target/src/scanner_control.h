/* SPDX-License-Identifier: MIT */
#pragma once
#include <stdbool.h>

enum yeti_scan_state { Y_SCAN_OFFLINE, Y_SCAN_RUNNING, Y_SCAN_FAULT };
/* Single scanner instance. Only init/scan owner publish lifecycle changes. */
enum yeti_scan_state yeti_scan_state(void);
bool yeti_scan_ready(void);
bool yeti_scan_fault(void);
int yeti_scan_submit(unsigned action);
/* Returns zero if empty, -EIO if a queued mutation lost a race to a fault. */
int yeti_scan_take(void);
