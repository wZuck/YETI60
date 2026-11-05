/* Host interfaces for unmodified pinned Zephyr NVS and CRC sources.
 * SPDX-License-Identifier: MIT */
#pragma once
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/types.h>

#define __packed __attribute__((packed))
#define BUILD_ASSERT(test, ...) _Static_assert(test, #test)
#define MIN(a,b) ((a)<(b)?(a):(b))
#define IS_ENABLED(option) 0 /* CONFIG_NVS_DATA_CRC is disabled in both targets. */
#define LOG_MODULE_REGISTER(...)
#define LOG_ERR(...) ((void)0)
#define LOG_WRN(...) ((void)0)
#define LOG_INF(...) ((void)0)
#define LOG_DBG(...) ((void)0)
#define K_FOREVER (-1)
struct k_mutex { bool held; };
static inline void k_mutex_init(struct k_mutex *mutex) { mutex->held=false; }
static inline void k_mutex_lock(struct k_mutex *mutex, int timeout) {
  (void)timeout; assert(!mutex->held); mutex->held=true;
}
static inline void k_mutex_unlock(struct k_mutex *mutex) {
  assert(mutex->held); mutex->held=false;
}
struct device { unsigned id; };
struct flash_parameters { size_t write_block_size; uint8_t erase_value; };
struct flash_pages_info { off_t start_offset; size_t size; uint32_t index; };
const struct flash_parameters *flash_get_parameters(const struct device *);
size_t flash_get_write_block_size(const struct device *);
int flash_get_page_info_by_offs(const struct device *, off_t, struct flash_pages_info *);
int flash_read(const struct device *, off_t, void *, size_t);
int flash_write(const struct device *, off_t, const void *, size_t);
int flash_flatten(const struct device *, off_t, size_t);
uint8_t crc8_ccitt(uint8_t, const void *, size_t);
uint8_t crc8_rohc(uint8_t, const void *, size_t);
uint32_t crc32_ieee(const uint8_t *, size_t);
uint32_t crc32_ieee_update(uint32_t, const uint8_t *, size_t);
