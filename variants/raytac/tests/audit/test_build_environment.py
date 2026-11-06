#!/usr/bin/env python3
"""Guard fresh-build errors and keep existing developer workspaces intact."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import yeti60_build_environment as environment
import prepare_yeti60_workspace as prepare


class BuildEnvironment(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='yeti60-env-test-')
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name) / 'workspace'
        self.lock = ROOT / 'firmware/target/config/west.yml'

    def manifest(self, settings='[manifest]\npath=config\nfile=west.yml\n'):
        (self.workspace / 'config').mkdir(parents=True)
        (self.workspace / 'config/west.yml').write_bytes(self.lock.read_bytes())
        (self.workspace / '.west').mkdir()
        (self.workspace / '.west/config').write_text(settings)

    def test_missing_workspace_has_actionable_error_before_python_import(self):
        result = subprocess.run([sys.executable, str(ROOT/'scripts/build_yeti60_firmware.py'),
                                 '--workspace', str(self.workspace)], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('prepare_yeti60_workspace.py', result.stderr)
        self.assertNotIn('ModuleNotFoundError', result.stderr)
        self.assertNotIn('Traceback', result.stderr)
        self.assertFalse(self.workspace.exists())

    def test_changed_manifest_is_rejected_without_overwrite(self):
        self.manifest()
        path = self.workspace / 'config/west.yml'
        changed = path.read_bytes() + b'# local edit\n'
        path.write_bytes(changed)
        with self.assertRaisesRegex(SystemExit, 'differs'):
            environment.check_manifest(self.workspace, self.lock)
        self.assertEqual(path.read_bytes(), changed)

    def test_selection_overrides_are_rejected(self):
        for settings in ['path=other\n', 'path=config\nfile=other.yml\n',
                         'path=config\ngroup-filter=-hal\n', 'path=config\nproject-filter=-zmk\n']:
            with self.subTest(settings=settings), tempfile.TemporaryDirectory() as directory:
                original = self.workspace
                self.workspace = Path(directory)
                self.manifest('[manifest]\n' + settings)
                with self.assertRaisesRegex(SystemExit, 'configuration differs'):
                    environment.check_manifest(self.workspace, self.lock)
                self.workspace = original

    def test_incomplete_workspace_is_rejected_before_dtlib_import(self):
        self.manifest()
        with self.assertRaisesRegex(SystemExit, 'Pinned Zephyr is missing'):
            environment.require_workspace(self.workspace, self.lock)

    def test_environment_override_is_shared_by_all_target_consumers(self):
        with patch.dict(os.environ, {'YETI60_ZMK_WORKSPACE': str(self.workspace)}):
            self.assertEqual(environment.workspace_path(), self.workspace.resolve())
            for name in ['check_yeti60_target', 'test_yeti60_key_pipeline', 'test_yeti60_nvs_powercut',
                         'test_yeti60_usb_events', 'test_yeti60_scan_control',
                         'test_yeti60_recovery', 'test_yeti60_gpio_modes']:
                with self.subTest(name=name):
                    spec = importlib.util.spec_from_file_location('fixture_' + name, ROOT/'scripts'/(name+'.py'))
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    self.assertEqual(getattr(module, 'WORKSPACE', module.workspace_path()), self.workspace.resolve())

    def test_nonempty_directory_is_left_intact(self):
        self.workspace.mkdir()
        sentinel = self.workspace / 'important.txt'
        sentinel.write_text('keep this')
        with patch.object(sys, 'argv', ['prepare', '--workspace', str(self.workspace)]), \
                patch.object(prepare.shutil, 'which', return_value='/available'), \
                patch.object(prepare.subprocess, 'run', return_value=SimpleNamespace(returncode=0)):
            with self.assertRaisesRegex(SystemExit, 'Nonempty directory'):
                prepare.main()
        self.assertEqual(list(self.workspace.iterdir()), [sentinel])
        self.assertEqual(sentinel.read_text(), 'keep this')

    def test_dependency_head_drift_does_not_run_checkout(self):
        calls = []
        def run(command, **kwargs):
            calls.append(command)
            return SimpleNamespace(returncode=0, stdout='local-commit\n')
        with patch.object(prepare.subprocess, 'check_output', return_value='zmk|locked-commit\n'), \
                patch.object(prepare.subprocess, 'run', side_effect=run):
            with self.assertRaisesRegex(SystemExit, 'left unchanged'):
                prepare.dependencies(['docker'], self.workspace, complete=False)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][-2:], ['rev-parse', 'HEAD'])

    def test_dirty_dependency_does_not_run_update(self):
        with patch.object(prepare.subprocess, 'check_output', side_effect=['zmk|locked\n', b' M source.c\n']), \
                patch.object(prepare.subprocess, 'run', return_value=SimpleNamespace(returncode=0, stdout='locked\n')):
            with self.assertRaisesRegex(SystemExit, 'left unchanged'):
                prepare.dependencies(['docker'], self.workspace, complete=False)

    def test_docker_invisible_manifest_has_mount_guidance(self):
        with patch.object(prepare.subprocess, 'run', return_value=SimpleNamespace(returncode=1, stdout=b'')):
            with self.assertRaisesRegex(SystemExit, 'Share/mount'):
                prepare.visible_manifest(['docker'])

    def test_container_is_pinned_and_global_selection_is_disabled(self):
        self.workspace.mkdir()
        command = environment.docker_base(self.workspace)
        self.assertIn(environment.IMAGE, command)
        self.assertIn('@sha256:', environment.IMAGE)
        self.assertIn('WEST_CONFIG_GLOBAL=/dev/null', command)
        self.assertIn('WEST_CONFIG_SYSTEM=/dev/null', command)


if __name__ == '__main__':
    unittest.main()
