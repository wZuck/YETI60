"""Shared location and preflight for the pinned YETI60 west workspace."""
import configparser
import os
from pathlib import Path

IMAGE = 'zmkfirmware/zmk-build-arm@sha256:edb1c953438c6f720ddb79c3762f3972013b7fbbaf4fff3592fc869983e7afc5'
CONTAINER_EXEC = '''import os, subprocess, sys
if os.path.isfile('/work/.west/config'):
    paths = subprocess.check_output(['west', 'list', '-f', '{abspath}'], text=True).splitlines()
    for path in paths:
        subprocess.run(['git', 'config', '--global', '--add', 'safe.directory', path], check=True)
os.execvp(sys.argv[1], sys.argv[1:])
'''


def workspace_path():
    return Path(os.environ.get('YETI60_ZMK_WORKSPACE',
                               '~/.cache/yeti60-zmk-workspace')).expanduser().resolve()


def check_manifest(workspace, lock):
    config = workspace / 'config/west.yml'
    if not config.is_file() or config.read_bytes() != lock.read_bytes():
        raise SystemExit('Workspace manifest is missing or differs from the committed lock: '
                         + str(config) + '; use scripts/prepare_yeti60_workspace.py')
    settings = configparser.ConfigParser()
    settings.read(workspace / '.west/config')
    if (settings.get('manifest', 'path', fallback='') != 'config' or
            settings.get('manifest', 'file', fallback='west.yml') != 'west.yml' or
            settings.has_option('manifest', 'group-filter') or
            settings.has_option('manifest', 'project-filter')):
        raise SystemExit('Workspace configuration differs from the frozen manifest selection: '
                         + str(workspace / '.west/config'))


def require_workspace(workspace, lock):
    check_manifest(workspace, lock)
    if not (workspace / 'zephyr/scripts/dts/python-devicetree/src/devicetree/dtlib.py').is_file():
        raise SystemExit('Pinned Zephyr is missing; run scripts/prepare_yeti60_workspace.py '
                         '--workspace ' + str(workspace))


def docker_base(workspace):
    # Ignore machine-wide west selection overrides in the build container.
    command = ['docker', 'run', '--rm', '-e', 'WEST_CONFIG_SYSTEM=/dev/null',
               '-e', 'WEST_CONFIG_GLOBAL=/dev/null', '-e', 'CMAKE_BUILD_PARALLEL_LEVEL=2',
               '-v', f'{workspace}:/work']
    # Developer reference clones may use external object stores. Normal fresh
    # network clones have none. Keep the existing stores read-only, at their paths.
    roots = set()
    for alternates in workspace.rglob('objects/info/alternates'):
        for path in alternates.read_text().splitlines():
            store = (alternates.parent.parent / path).resolve() if not Path(path).is_absolute() else Path(path)
            roots.add(store.parents[2])
    for directory in sorted(roots):
        command += ['-v', f'{directory}:{directory}:ro']
    return command + ['-w', '/work', IMAGE, 'python3', '-c', CONTAINER_EXEC]


def add_mounts(command, mounts):
    """Insert mount options before the image/command, without shell quoting."""
    at = command.index(IMAGE)
    command[at:at] = mounts
