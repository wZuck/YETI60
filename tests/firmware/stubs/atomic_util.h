#pragma once
/* The host test is single-threaded; interrupt timing is an on-device test. */
#define ATOMIC_BLOCK_FORCEON for (bool once = true; once; once = false)
