English | [Chinese](firmware-environment.zh-CN.md)

# Build the Raytac firmware from a fresh checkout

For normal assembly, use the [matched current HEX downloads](../../hardware/usb-short-route/firmware/README.md). This procedure is for rebuilding them. Run commands from the YETI60 repository root; do not substitute the reference board firmware for the current USB-short-route candidate.

## Required host software

- Python 3.9 or later and Git on the host.
- A running Linux-container Docker engine, with the checkout and workspace directories shared into its VM. Docker Desktop and Colima need access to those host paths. A directory under the host's temporary folder may not be shared; the default workspace under the home directory avoids that issue on the tested Colima setup.
- Internet access **from the container** to the image registry and the Git URLs in the manifest. A host browser connection does not establish container connectivity. Additional free disk space is needed for the image, dependencies and build directories.
- A host C compiler with AddressSanitizer/UndefinedBehaviorSanitizer for the candidate wrapper's native tests. The recorded macOS checks use Clang. No physical keyboard or probe is needed for compilation and these tests.

The host does not need a separately installed west, Zephyr SDK or Python `devicetree` package. The build image supplies west/the ARM toolchain; host scripts load the device-tree parser from the locked Zephyr checkout. The [frozen manifest](../../firmware/target/config/west.yml) pins 56 active dependencies, including the project ZMK fork and Zephyr. The container is pinned to `zmkfirmware/zmk-build-arm@sha256:edb1c953438c6f720ddb79c3762f3972013b7fbbaf4fff3592fc869983e7afc5`.

## Initialize and verify

```sh
python3 variants/raytac/scripts/prepare_yeti60_workspace.py
python3 variants/raytac/scripts/prepare_yeti60_workspace.py --check
```

The first command copies the exact manifest into `~/.cache/yeti60-zmk-workspace/config/west.yml`, initializes west locally, downloads the locked dependencies, runs `west zephyr-export`, and verifies their commits and clean working trees. It pulls the pinned image only when needed. Repeating it can resume an interrupted download; it does not reset or clean dependency repositories. A nonempty unrelated directory, changed manifest, changed dependency commit, tracked edit or untracked source file stops preparation with the existing contents retained. Choose another workspace if you intentionally maintain modified dependencies.

`--check` checks the existing workspace and image without downloading, updating or exporting. It still needs the Docker daemon. Both commands reject local west project/group selection overrides and disable global/system selection overrides inside the container. Git ownership exceptions are limited to the manifest directories inside each disposable container; host Git configuration is unchanged. Compilation uses two parallel jobs to limit file-descriptor pressure on shared VM filesystems.

For a different workspace, select the **same path for preparation, build and tests**:

```sh
export YETI60_ZMK_WORKSPACE="$HOME/.cache/yeti60-raytac-workspace"
python3 variants/raytac/scripts/prepare_yeti60_workspace.py
python3 variants/raytac/scripts/prepare_yeti60_workspace.py --check
```

The builders also accept `--workspace <path>`; the environment variable additionally selects it for independently invoked target/host checks. Leave it set throughout the session when using a custom path. Paths containing spaces are supported; Docker bind paths containing a colon are unsupported.

## Reuse a verified dependency cache

If another workspace already contains the exact lock, west can clone from it without redownloading project histories:

```sh
python3 variants/raytac/scripts/prepare_yeti60_workspace.py \
  --workspace "$HOME/.cache/yeti60-raytac-workspace" \
  --cache-workspace "$HOME/.cache/yeti60-zmk-workspace"
export YETI60_ZMK_WORKSPACE="$HOME/.cache/yeti60-raytac-workspace"
python3 variants/raytac/scripts/prepare_yeti60_workspace.py --check
```

Use a new destination for the first cache-based initialization. The source cache is checked against the same manifest and mounted read-only. The destination has separate checkouts. The image must already be available to work offline; the cache is not a substitute for the exact pins or for recording build provenance. Developer caches that use Git alternates also need the original object stores to remain available; ordinary network clones do not require them.

## Rebuild the current board

The candidate wrapper checks the published native/CAD evidence before building. With the current committed bundle:

```sh
python3 variants/raytac/scripts/build_usb_short_firmware.py
python3 variants/raytac/scripts/check_usb_short_firmware.py
```

It builds **both normal and calibrator** ARM targets, checks the linked USB/HID structures and calibration contract, and runs the native scan, GPIO, key pipeline and NVS tests. Current candidate HEX/BIN files and evidence are published under `variants/raytac/hardware/usb-short-route/firmware/`. ELF files and intermediate builds remain in `variants/raytac/.assembly-work/usb-short-build/` and are recorded by hash. The candidate build leaves the separate reference releases untouched.

`--host-tests-only` needs a previous successful local build and matching unchanged firmware inputs. It is not a first-build shortcut. Changing the board or firmware contract requires a full build. The separate `build_yeti60_firmware.py` builds the retained reference board under `firmware/releases/`; use it only for reference engineering work.

## Diagnose failures

| Message/symptom | Action |
|---|---|
| Docker daemon/image unavailable | Start Docker; run preparation without `--check` to download the pinned image. |
| Docker cannot read the host manifest | Share the workspace path with Docker/Colima; retry the same command or use the default home-directory path. |
| Fetch stalls/fails | Check DNS, HTTPS/proxy and registry access inside the container. Retry preparation after restoring connectivity; existing downloads are retained. |
| Manifest/commit/working-tree mismatch | Keep the existing work; use a separate fresh workspace with the committed lock. Do not delete local edits to make the check pass. |
| Pinned Zephyr or manifest missing | Run preparation first; do not install a random host `devicetree` package. |
| Stale native/CAD or firmware evidence | Re-run the corresponding design checks/full build after intentional source changes; do not edit recorded hashes to hide the mismatch. |
| Target compilation fails | Inspect `.assembly-work/usb-short-build/.firmware-work/normal.log` or `calibrator.log` under the Raytac directory. |

The west initialization/update sequence follows [Zephyr's built-in-command documentation](https://docs.zephyrproject.org/latest/develop/west/built-in.html). Passing builds and host tests do not verify physical USB enumeration, BLE radio operation, EC margins, charging safety or fit. Continue with the [open-bench acceptance sequence](../../OPEN-BENCH.md) for the manufactured board.

## Recorded validation and boundaries

The [fresh-source build evidence](../audit/published-source-build.json) records successful normal/calibrator builds and target/host checks from a source fixture without copied local project build directories, using a separate 56-dependency workspace created from a read-only locked cache. Rebuilt HEX/BIN bytes and calibration identifiers are unchanged. Ten environment regression checks accompany this update.

GitHub HTTPS timeout/TLS failures in the current Colima VM prevented completion of internet-only first-time downloading; that route is not counted as passed. Independent dependency-workspace creation and compilation are verified separately from network connectivity.

Native KiCad 3D models still need a separate repair: legacy KiCad 6/private references, duplicate U2/U4 models and a J2 SMT connector model absent from the tested library. Those items are outside this firmware-build pass. The independent assembly renderer and native KiCad 3D view use different model sources; neither establishes the other's acceptance.
