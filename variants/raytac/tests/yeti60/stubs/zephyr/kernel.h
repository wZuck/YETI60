/* Deterministic host workqueue double; no native Zephyr scheduler is executed. */
#pragma once
#include <stdbool.h>
struct k_work { void (*handler)(struct k_work *); bool pending; };
#define K_WORK_DEFINE(name, callback) struct k_work name = {callback, false}
int k_work_submit(struct k_work *);
