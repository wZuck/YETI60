#!/usr/bin/env python3
"""Initialize/check a frozen west workspace using only host Python/Git/Docker."""
import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from yeti60_build_environment import (IMAGE, add_mounts, check_manifest, docker_base,
                                      require_workspace, workspace_path)

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / 'firmware/target/config/west.yml'


def visible_manifest(base):
    result = subprocess.run(base + ['cat', '/work/config/west.yml'], capture_output=True)
    if result.returncode or result.stdout != LOCK.read_bytes():
        raise SystemExit('Docker cannot read the host workspace manifest. Share/mount the '
                         'workspace directory with Docker (including Colima), then retry; '
                         'the default ~/.cache path is recommended.')


def container(workspace, cache):
    base = docker_base(workspace)
    if cache is not None:
        # Preserve cache object-store paths for reference clones; mount every
        # source read-only. west clones into the new workspace, never the cache.
        extra = ['-v', f'{cache}:{cache}:ro']
        cached = docker_base(cache)
        for at, argument in enumerate(cached):
            if argument == '-v' and cached[at + 1] != f'{cache}:/work':
                extra += ['-v', cached[at + 1]]
        add_mounts(base, extra)
    return base


def dependencies(base, workspace, complete):
    lines = subprocess.check_output(base + ['west', 'list', '-f', '{path}|{revision}'],
                                    text=True).splitlines()
    revisions = {}
    for line in lines:
        name, locked = line.split('|')
        if name == 'config':
            continue
        directory = workspace / name
        head = subprocess.run(['git', '-C', str(directory), 'rev-parse', 'HEAD'],
                              text=True, capture_output=True)
        if head.returncode:
            if complete:
                raise SystemExit('Dependency is missing: ' + name)
            continue
        if head.stdout.strip() != locked:
            raise SystemExit('Dependency revision differs from lock; left unchanged: ' + name)
        dirty = subprocess.check_output(['git', '-C', str(directory), 'status',
                                         '--porcelain', '--untracked-files=normal'])
        if dirty:
            raise SystemExit('Modified/untracked dependency files; left unchanged: ' + name)
        revisions[name] = locked
    return revisions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, default=workspace_path())
    parser.add_argument('--check', action='store_true', help='Verify existing workspace without updating it or pulling an image')
    parser.add_argument('--cache-workspace', type=Path,
                        help='Clone dependencies from a separately verified locked workspace mounted read-only')
    args = parser.parse_args()
    workspace = args.workspace.expanduser().resolve()
    cache = args.cache_workspace.expanduser().resolve() if args.cache_workspace else None
    if cache == workspace:
        raise SystemExit('Cache and destination workspaces must differ')
    for executable in ('git', 'docker'):
        if not shutil.which(executable):
            raise SystemExit('Install ' + executable + ' first; see docs/build/firmware-environment.md')
    subprocess.run(['docker', 'info'], check=True, stdout=subprocess.DEVNULL)
    image = subprocess.run(['docker', 'image', 'inspect', IMAGE], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)
    if image.returncode:
        if args.check:
            raise SystemExit('Pinned build image is missing; run preparation without --check')
        subprocess.run(['docker', 'pull', IMAGE], check=True)
    if cache is not None:
        require_workspace(cache, LOCK)
        dependencies(docker_base(cache), cache, complete=True)
    if args.check:
        require_workspace(workspace, LOCK)
    else:
        marker = workspace / '.yeti60-workspace.json'
        expected = {'manifest_sha256': hashlib.sha256(LOCK.read_bytes()).hexdigest(),
                    'container': IMAGE}
        if not (workspace / '.west/config').exists():
            if workspace.exists() and any(workspace.iterdir()):
                if not marker.is_file() or json.loads(marker.read_text()) != expected:
                    raise SystemExit('Nonempty directory is not a resumable YETI60 workspace; left unchanged: '
                                     + str(workspace))
            (workspace / 'config').mkdir(parents=True, exist_ok=True)
            config = workspace / 'config/west.yml'
            if config.exists() and config.read_bytes() != LOCK.read_bytes():
                raise SystemExit('Existing manifest differs; left unchanged: ' + str(config))
            marker.write_text(json.dumps(expected, indent=2) + '\n')
            config.write_bytes(LOCK.read_bytes())
            visible_manifest(container(workspace, cache))
            subprocess.run(container(workspace, cache) + ['west', 'init', '-l', 'config'], check=True)
        check_manifest(workspace, LOCK)
    base = container(workspace, cache)
    visible_manifest(base)
    dependencies(base, workspace, complete=args.check)
    if not args.check:
        options = ['--path-cache', str(cache)] if cache is not None else []
        subprocess.run(base + ['west', 'update', *options], check=True)
        subprocess.run(base + ['west', 'zephyr-export'], check=True)
        require_workspace(workspace, LOCK)
    revisions = dependencies(base, workspace, complete=True)
    print(f'Pinned workspace verified: {len(revisions)} dependencies at {workspace}', flush=True)


if __name__ == '__main__':
    main()
