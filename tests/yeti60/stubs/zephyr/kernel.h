/* Deterministic host workqueue double; no native Zephyr scheduler is executed. */
#pragma once
#include <stdbool.h>
struct k_work { void (*handler)(struct k_work *); bool pending; };
#define K_WORK_DEFINE(name, callback) struct k_work name = {callback, false}
int k_work_submit(struct k_work *);
#include <assert.h>
#define BUILD_ASSERT(condition, ...) _Static_assert(condition, #condition)
struct k_spinlock { bool held; };
typedef int k_spinlock_key_t;
static inline k_spinlock_key_t k_spin_lock(struct k_spinlock *lock) {
  assert(!lock->held); lock->held = true; return 0;
}
static inline void k_spin_unlock(struct k_spinlock *lock, k_spinlock_key_t key) {
  (void)key; assert(lock->held); lock->held = false;
}
