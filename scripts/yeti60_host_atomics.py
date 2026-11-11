"""Use the pinned Zephyr GCC/Clang atomic implementation in native fixtures."""
import hashlib
import subprocess

REV = '10ba6d0cb38bc3d258775d27982f707599320085'


def prepare(workspace, folder):
    hashes = {}
    for name in ['atomic_types.h', 'atomic_builtin.h']:
        rel = 'include/zephyr/sys/' + name
        data = subprocess.check_output(['git', '-C', str(workspace/'zephyr'),
                                        'show', REV+':'+rel])
        path = folder/'zephyr/sys'/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        hashes[rel] = hashlib.sha256(data).hexdigest()
    (folder/'zephyr/sys/atomic.h').write_text(
        '/* Select pinned builtin atomics for this host fixture. */\n'
        '#include <zephyr/sys/atomic_builtin.h>\n')
    return hashes
