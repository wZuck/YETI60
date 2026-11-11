/* Actual NVS C on a bounded NOR flash model, not NVMC or electrical emulation.
 * SPDX-License-Identifier: MIT */
#include "nvs_shim.h"
#include "core.h"
#include "calibration.h"
#include "nvs_profile.h"
#include <zephyr/fs/nvs.h>
#include <zephyr/sys/atomic.h>
#include <errno.h>
#include <setjmp.h>
#include <stdlib.h>

enum { FLASH_BYTES=0x100000, CAL_ID=42, SENTINEL_ID=10, FILLER_ID=99 };
static uint8_t flash_image[FLASH_BYTES], baseline[FLASH_BYTES];
static const uint8_t sentinel[64]="YETI60 unrelated setting sentinel; NOT a real Bluetooth bond";
static const struct device flash_device={0};
static const struct flash_parameters parameters={WRITE_BYTES,0xff};
static struct nvs_fs fs;
static struct yeti_calibration old_record, new_record;
static jmp_buf power_loss;
static unsigned units, erase_calls, dirty_erases, cut_at, pattern;
static unsigned first_erase_unit;
static bool armed;
static unsigned recovered_old, recovered_new, rejected, trials;
typedef ssize_t (*settings_read_cb)(void *, void *, size_t);
static struct yeti_calibration saved;
static atomic_t calibration_loaded;
#define YETI_CALIBRATION_VERSION CALIBRATION_VERSION
#include "scanner_load.inc"
static ssize_t read_calibration(void *arg, void *data, size_t len) {
  ssize_t rc=nvs_read(arg,CAL_ID,data,len);
  return rc>(ssize_t)len?(ssize_t)len:rc;
}

static void bounds(off_t offset, size_t size) {
  assert(offset>=NVS_OFFSET && (uint64_t)offset+size<=NVS_OFFSET+SECTOR_BYTES*SECTOR_COUNT);
}
const struct flash_parameters *flash_get_parameters(const struct device *dev) {
  assert(dev==&flash_device); return &parameters;
}
size_t flash_get_write_block_size(const struct device *dev) {
  assert(dev==&flash_device); return WRITE_BYTES;
}
int flash_get_page_info_by_offs(const struct device *dev, off_t offset, struct flash_pages_info *info) {
  assert(dev==&flash_device); bounds(offset,1);
  *info=(struct flash_pages_info){offset-offset%SECTOR_BYTES,SECTOR_BYTES,(uint32_t)(offset/SECTOR_BYTES)};
  return 0;
}
int flash_read(const struct device *dev, off_t offset, void *data, size_t size) {
  assert(dev==&flash_device); bounds(offset,size); memcpy(data,flash_image+offset,size); return 0;
}
static void program_byte(off_t offset, uint8_t data, uint8_t mask) {
  uint8_t selected=(uint8_t)(data | (uint8_t)~mask);
  assert((flash_image[offset]&data)==data); /* No un-erased rewrite. */
  flash_image[offset]&=selected;
}
static void mutation(off_t offset, const uint8_t *data, bool erase) {
  assert(WRITE_BYTES==4);
  if (armed && units==cut_at) {
    for (unsigned byte=0;byte<WRITE_BYTES;byte++) {
      uint8_t mask=0;
      if (pattern<=3 && byte<pattern) mask=255;
      if (pattern==4) mask=0x55;
      if (pattern==5) mask=0xaa;
      if (erase) flash_image[offset+byte]|=mask;
      else program_byte(offset+byte,data[byte],mask);
    }
    longjmp(power_loss,1);
  }
  for (unsigned byte=0;byte<WRITE_BYTES;byte++) {
    if (erase) flash_image[offset+byte]=255;
    else program_byte(offset+byte,data[byte],255);
  }
  units++;
}
int flash_write(const struct device *dev, off_t offset, const void *data, size_t size) {
  assert(dev==&flash_device); bounds(offset,size);
  assert(offset%WRITE_BYTES==0 && size%WRITE_BYTES==0);
  for (size_t i=0;i<size;i+=WRITE_BYTES) mutation(offset+i,(const uint8_t *)data+i,false);
  return 0;
}
int flash_flatten(const struct device *dev, off_t offset, size_t size) {
  assert(dev==&flash_device); bounds(offset,size);
  assert(offset%SECTOR_BYTES==0 && size==SECTOR_BYTES);
  erase_calls++;
  if (erase_calls==1) first_erase_unit=units;
  for (size_t i=0;i<size;i++) if (flash_image[offset+i]!=255) { dirty_erases++; break; }
  for (size_t i=0;i<size;i+=WRITE_BYTES) mutation(offset+i,NULL,true);
  return 0;
}
static void mount_fresh(void) {
  fs=(struct nvs_fs){.offset=NVS_OFFSET,.sector_size=SECTOR_BYTES,
                     .sector_count=SECTOR_COUNT,.flash_device=&flash_device};
  int rc=nvs_mount(&fs);
  if (rc) fprintf(stderr,"Mount failed: %d at cut=%u pattern=%u\n",rc,cut_at,pattern);
  assert(rc==0 && fs.ready);
}
static void make_record(struct yeti_calibration *record, unsigned low, unsigned high) {
  *record=(struct yeti_calibration){.version=CALIBRATION_VERSION};
  for (unsigned r=0;r<YETI_ROWS;r++) for (unsigned c=0;c<YETI_COLS;c++) {
    record->low[r][c]=low; record->high[r][c]=high;
  }
  record->crc32=yeti_calibration_checksum(record);
  assert(yeti_calibration_valid(record,CALIBRATION_VERSION));
}
static void initial(const char *scenario) {
  memset(flash_image,0xa5,NVS_OFFSET);
  memset(flash_image+NVS_OFFSET,255,SECTOR_BYTES*SECTOR_COUNT);
  memset(flash_image+NVS_OFFSET+SECTOR_BYTES*SECTOR_COUNT,0x5a,
         FLASH_BYTES-NVS_OFFSET-SECTOR_BYTES*SECTOR_COUNT);
  mount_fresh();
  assert(nvs_write(&fs,SENTINEL_ID,sentinel,sizeof(sentinel))==sizeof(sentinel));
  if (strcmp(scenario,"first-save")) {
    size_t size=!strcmp(scenario,"legacy-replacement")?304:sizeof(old_record);
    assert(nvs_write(&fs,CAL_ID,&old_record,size)==(ssize_t)size);
  }
}
static void prepare_gc(void) {
  uint8_t filler[256];
  for (unsigned attempt=0;attempt<1000;attempt++) {
    memcpy(baseline,flash_image,sizeof(baseline)); struct nvs_fs before=fs;
    units=erase_calls=dirty_erases=0;
    assert(nvs_write(&fs,CAL_ID,&new_record,sizeof(new_record))==sizeof(new_record));
    bool found=dirty_erases>0;
    memcpy(flash_image,baseline,sizeof(baseline)); fs=before;
    if (found) { printf("GC baseline after %u filler updates\n",attempt); return; }
    memset(filler,(uint8_t)attempt,sizeof(filler)); memcpy(filler,&attempt,sizeof(attempt));
    assert(nvs_write(&fs,FILLER_ID,filler,sizeof(filler))==sizeof(filler));
  }
  assert(!"Could not reach dirty garbage collection baseline");
}
static void verify(const char *scenario) {
  uint8_t value[64];
  assert(nvs_read(&fs,SENTINEL_ID,value,sizeof(value))==sizeof(value));
  assert(!memcmp(value,sentinel,sizeof(value)));
  struct yeti_calibration record;
  ssize_t size=nvs_read(&fs,CAL_ID,&record,sizeof(record));
  atomic_clear(&calibration_loaded); memset(&saved,0,sizeof(saved));
  int rc=size<0?(int)size:load_calibration("thresholds",(size_t)size,read_calibration,&fs);
  if (!rc) {
    assert(atomic_get(&calibration_loaded) && size==sizeof(saved));
    assert(yeti_calibration_valid(&saved,CALIBRATION_VERSION));
    if (!memcmp(&saved,&new_record,sizeof(saved))) recovered_new++;
    else {
      assert(strcmp(scenario,"first-save") && strcmp(scenario,"legacy-replacement"));
      assert(!memcmp(&saved,&old_record,sizeof(saved))); recovered_old++;
    }
  } else {
    assert(!atomic_get(&calibration_loaded));
    /* First/legacy save can remain uncalibrated; a prior valid record must survive. */
    assert(!strcmp(scenario,"first-save") || !strcmp(scenario,"legacy-replacement"));
    assert(size==-ENOENT || size==304); rejected++;
  }
  /* Recovery must also permit a subsequent calibration save and readback. */
  struct yeti_calibration retry;
  make_record(&retry,1200,1900);
  assert(nvs_write(&fs,CAL_ID,&retry,sizeof(retry))==sizeof(retry));
  assert(nvs_read(&fs,CAL_ID,&record,sizeof(record))==sizeof(record));
  assert(yeti_calibration_valid(&record,CALIBRATION_VERSION));
  assert(!memcmp(&record,&retry,sizeof(record)));
  assert(nvs_read(&fs,SENTINEL_ID,value,sizeof(value))==sizeof(value));
  assert(!memcmp(value,sentinel,sizeof(value)));
  assert(!memcmp(flash_image,baseline,NVS_OFFSET));
  unsigned end=NVS_OFFSET+SECTOR_BYTES*SECTOR_COUNT;
  assert(!memcmp(flash_image+end,baseline+end,FLASH_BYTES-end));
}
static void trial(const char *scenario, unsigned cutoff, unsigned mode) {
  bool recovery=!strcmp(scenario,"recovery-cut");
  memcpy(flash_image,baseline,sizeof(baseline));
  if (!recovery) mount_fresh();
  cut_at=cutoff; pattern=mode; units=erase_calls=dirty_erases=0; armed=true;
  if (!setjmp(power_loss)) {
    if (recovery) mount_fresh();
    else assert(nvs_write(&fs,CAL_ID,&new_record,sizeof(new_record))==sizeof(new_record));
    /* Cut after final commit, before the caller could observe completion. */
    assert(units==cut_at); longjmp(power_loss,1);
  }
  armed=false; mount_fresh(); verify(scenario); trials++;
}
static void damaged_gc_baseline(unsigned cutoff) {
  memcpy(flash_image,baseline,sizeof(baseline)); mount_fresh();
  cut_at=cutoff; pattern=4; units=erase_calls=dirty_erases=0; armed=true;
  if (!setjmp(power_loss)) {
    (void)nvs_write(&fs,CAL_ID,&new_record,sizeof(new_record));
    assert(!"Expected an initial mid-erase cut");
  }
  armed=false;
  memcpy(baseline,flash_image,sizeof(baseline));
}
int main(int argc, char **argv) {
  assert(argc==2); const char *scenario=argv[1];
  assert(!strcmp(scenario,"first-save") || !strcmp(scenario,"rewrite") ||
         !strcmp(scenario,"legacy-replacement") || !strcmp(scenario,"garbage-collection") ||
         !strcmp(scenario,"recovery-cut"));
  make_record(&old_record,1000,1500); make_record(&new_record,1100,1700);
  initial(scenario);
  bool recovery=!strcmp(scenario,"recovery-cut");
  if (!strcmp(scenario,"garbage-collection") || recovery) prepare_gc();
  memcpy(baseline,flash_image,sizeof(baseline));
  units=erase_calls=dirty_erases=0;
  assert(nvs_write(&fs,CAL_ID,&new_record,sizeof(new_record))==sizeof(new_record));
  if (recovery) {
    assert(dirty_erases>0);
    damaged_gc_baseline(first_erase_unit+SECTOR_BYTES/WRITE_BYTES/2);
    units=erase_calls=dirty_erases=0; mount_fresh();
  }
  unsigned total=units, erases=erase_calls, dirty=dirty_erases;
  assert(total>0);
  if (!strcmp(scenario,"garbage-collection") || recovery) assert(dirty>0);
  for (unsigned cutoff=0;cutoff<total;cutoff++)
    for (unsigned mode=0;mode<6;mode++) trial(scenario,cutoff,mode);
  trial(scenario,total,0);
  if (recovery) assert(recovered_old && !recovered_new && !rejected);
  else assert(recovered_new && (!strcmp(scenario,"first-save") || !strcmp(scenario,"legacy-replacement") || recovered_old));
  printf("{\"scenario\":\"%s\",\"program_or_erase_units\":%u,\"erase_calls\":%u,\"dirty_erases\":%u,\"trials\":%u,\"old\":%u,\"new\":%u,\"uncalibrated\":%u}\n",
         scenario,total,erases,dirty,trials,recovered_old,recovered_new,rejected);
  return 0;
}
