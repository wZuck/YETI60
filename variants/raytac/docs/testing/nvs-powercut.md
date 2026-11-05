English | [Chinese](nvs-powercut.zh-CN.md)

# NVS interruption and recovery model

The Raytac checks now execute the pinned Zephyr NVS implementation and the actual calibration loader against a bounded NOR flash model. **14,795 modeled interruption/recovery trials pass**, including garbage collection and a second interruption during recovery. This adds evidence without changing production firmware, PCB, materials or calibration identifiers. No reflash or recapture is required solely for this test update.

This is software recovery evidence, not an electrical power-cut test. Actual NVMC, battery/charger brownout, flash timing, endurance and real Bluetooth settings remain first-board work.

## Actual inputs and modeled hardware

The [recipe](../../scripts/test_yeti60_nvs_powercut.py) reads the normal ARM build's resolved configuration and device tree, compares their hashes to the build manifest, and checks all compiled-source hashes before testing. It uses the fixed Zephyr revision `10ba6d0cb38bc3d258775d27982f707599320085` from the dependency lock.

| Parameter | Value and basis |
|---|---|
| Reserved settings partition | `0xF0000–0xFFFFF`, 64 KiB, resolved device tree |
| NVS area actually used by this backend | Eight 4 KiB sectors, 32 KiB, derived from `SETTINGS_NVS_SECTOR_COUNT`, `SETTINGS_NVS_SECTOR_SIZE_MULT` and partition limits |
| Write alignment | Four bytes, resolved flash device tree and disabled one-byte-write emulation |
| Hardware erase page size | 4 KiB; model subdivides a page into four-byte chunks for selected interruption patterns |
| Global NVS data CRC | Disabled, matching both ARM targets; calibration has its separate payload CRC |
| Calibration payload | 308 bytes, current board bundle's actual identifier and production checksum |
| Other-setting sentinel | One opaque 64-byte record; not a real Bluetooth bond or settings-name database |
| Guarded regions | Application bytes below `0xF0000` and the unused upper 32 KiB of the reserved settings partition |

NVS C, its public/private headers, CRC-8/CRC-32 code and builtin atomics are compiled unchanged from the pinned source. The production scanner's `load_calibration` body is extracted verbatim and consumes the recovered NVS record. The settings backend and Nordic driver are read and hashed to check profile derivation; they are not executed. The flash device, mutex and reboot interfaces are models. Source hashes identify each part.

The flash model enforces bounds, alignment and NOR programming without an erase. A simulated reboot discards the filesystem instance/lock and mounts NVS from retained flash bytes. Every accepted calibration goes through the actual length/version/CRC/threshold loader checks and publishes its loaded flag. Every trial also verifies that another complete calibration can be saved/read back after recovery and that the unrelated sentinel survives.

Primary sources: [pinned NVS implementation](https://github.com/zmkfirmware/zephyr/blob/10ba6d0cb38bc3d258775d27982f707599320085/subsys/fs/nvs/nvs.c), [settings backend geometry](https://github.com/zmkfirmware/zephyr/blob/10ba6d0cb38bc3d258775d27982f707599320085/subsys/settings/src/settings_nvs.c), and [Zephyr's description of data-before-metadata writes and startup recovery](https://docs.zephyrproject.org/latest/services/storage/nvs/nvs.html).

## Injection patterns and counts

For each modeled four-byte write or erase chunk, the test cuts before the chunk, after programming/erasing its first one/two/three bytes, or after applying selected `0x55`/`0xAA` bit masks. There is also one cut after the final committed operation, before the caller could observe its completion. Four-byte erase chunks are an artificial way to explore partial-page contents; they are not a claim that nRF52840 supports four-byte hardware erases or erases a page in that order.

Thus, for `U` modeled units, the number of trials is `6 × U + 1`:

| Scenario | Units | Trials | Recovered old / new / uncalibrated |
|---|---:|---:|---|
| First calibration save | 79 | 475 | 0 / 1 / 474 |
| Replace an existing valid calibration | 79 | 475 | 474 / 1 / 0 |
| Replace a legacy 304-byte record | 79 | 475 | 0 / 1 / 474 |
| Save while collecting a dirty sector | 1,204 | 7,225 | 7,224 / 1 / 0 |
| Interrupt recovery after an earlier mid-erase interruption | 1,024 | 6,145 | 6,145 / 0 / 0 |
| Total | | **14,795** | All sentinel and resave/readback checks pass |

A simple save uses 77 four-byte payload units (`308 / 4`) plus two allocation-entry units (`8 / 4`), totaling 79. The dirty-GC baseline is reached after 103 changing filler updates. In the recorded run its save uses two sector-close units, 97 units copying live payloads/entries, two GC-completion units, 1,024 erase chunks, then 79 new-record units: `2 + 97 + 2 + 1024 + 79 = 1204`.

For the recovery scenario, the first interruption applies a `0x55` selected-bit change midway through the dirty-sector erase. The second cut sweeps all modeled units/patterns of the resulting remount recovery. This qualifies that selected two-interruption setup, not arbitrary or indefinitely repeated interruptions.

The one new-record result in each ordinary save scenario is the final-commit-before-acknowledgement cut. Initial and legacy saves can otherwise remain uncalibrated. Where a valid prior calibration exists, these tested cuts retain a complete prior or committed new record. The model does not publish a partial threshold table.

Two deliberately broken temporary NVS variants must fail: committing allocation metadata before its payload, and omitting a live sentinel during garbage collection. The dependency checkout itself is untouched. ASan/UBSan cover the native executions.

## Reproduce and published evidence

From the repository root, with host Clang, Python, the pinned workspace, and already built normal/calibrator artifacts:

```sh
python3 variants/raytac/scripts/check_yeti60_target.py
python3 variants/raytac/scripts/test_yeti60_nvs_powercut.py
```

[Reference evidence](../audit/nvs-powercut.json) records the profile, build/configuration/device-tree hashes, upstream and project source hashes, all five cases and both rejected mutants. [Candidate evidence](../../hardware/usb-short-route/firmware/nvs-powercut.json) is independently generated inside the isolated candidate tree with its own board identifier.

For test-only changes with matching existing candidate ARM artifacts:

```sh
python3 variants/raytac/scripts/build_usb_short_firmware.py --host-tests-only
python3 variants/raytac/scripts/check_usb_short_firmware.py
```

The host-only mode checks the existing ARM sources/artifacts before republishing tests. It rejects stale firmware inputs; it cannot turn a changed firmware source into a verified build. A fresh checkout or firmware change still requires the full build command without this flag. The normal audit includes the NVS model and rejects missing trials, incompatible profiles, stale provenance or a physical-acceptance claim.

## Remaining acceptance

The model does not execute NVMC, radio-synchronized flash operations, the Zephyr scheduler, a full settings-name allocation/update sequence, actual Bluetooth bonding, voltage ramps or wear. It samples specified partial programming/erase states; it does not cover arbitrary bit orderings, all possible damaged pages or unlimited repeated cuts. A sentinel surviving is not proof that a real Bluetooth bond survives.

Use the [first-board bench procedure](../../OPEN-BENCH.md) and [calibration upgrade instructions](calibration-storage.md). Measure supply voltage during actual save/erase; test ordinary reset retention and controlled interruptions with the actual battery/charger arrangement. Verify valid calibration or a clearly uncalibrated state, usable subsequent save, untouched application/settings regions, and real Bluetooth profile retention. These physical results remain open.

The first comprehensive run found a stale guide input hash after the target firmware README update. The [follow-up record](../audit/nvs-guide-followup.json) preserves the initial failed matrix and records guide regeneration plus executed reruns. Other passing checks are retained only after verifying their relevant inputs remain unchanged and final integration passes.
