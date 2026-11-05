import copy
import importlib.util
import os
from pathlib import Path
import unittest
from unittest.mock import patch

if os.name == 'posix':
    spec = importlib.util.spec_from_file_location('clean', Path(__file__).resolve().parents[1] / 'scripts/recovery/clean_storage.py')
    clean = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(clean)

UUID = '11111111-1111-1111-1111-111111111111'


def inventory():
    return {'blockdevices': [
        {'path': '/dev/sdz', 'type': 'disk', 'size': 1000204886016, 'mountpoints': [None], 'children': [
            {'path': '/dev/sdz1', 'type': 'part', 'size': 1000203091968, 'fstype': 'ext4',
             'uuid': UUID, 'maj:min': '8:1', 'mountpoints': [None]}]},
        {'path': '/dev/sdb', 'type': 'disk', 'size': 500107862016, 'children': [
            {'path': '/dev/sdb3', 'type': 'part', 'fstype': 'LVM2_member', 'children': [
                {'path': '/dev/mapper/root', 'type': 'lvm', 'mountpoints': ['/']}]}]},
        {'path': '/dev/sdc', 'type': 'disk', 'size': 15479597056, 'children': [
            {'path': '/dev/sdc1', 'type': 'part', 'fstype': 'vfat', 'mountpoints': [None]}]},
    ]}


@unittest.skipUnless(os.name == 'posix', 'Linux block-device safety module')
class CleanStorageSafety(unittest.TestCase):
    def test_uuid_resolves_renamed_hdd_without_assuming_sda(self):
        tree = inventory()
        target = clean.validate_target(tree, UUID, '/dev/sdz1')
        self.assertEqual(target['path'], '/dev/sdz1')
        self.assertEqual(tree, inventory())

    def test_rejects_wrong_capacity_mounted_root_lvm_children_and_resolution(self):
        for field, value in [('size', 16_000_000_000), ('mountpoints', ['/']),
                             ('fstype', 'LVM2_member'), ('type', 'disk'), ('children', [{'type': 'lvm'}])]:
            tree = inventory()
            tree['blockdevices'][0]['children'][0][field] = value
            with self.assertRaises(clean.GateError, msg=field):
                clean.validate_target(tree, UUID, '/dev/sdz1')
        with self.assertRaises(clean.GateError):
            clean.validate_target(inventory(), UUID, '/dev/sdb3')

    def test_rejects_duplicate_uuid_and_unexpected_partition_table(self):
        tree = inventory()
        tree['blockdevices'].append(copy.deepcopy(tree['blockdevices'][0]))
        with self.assertRaises(clean.GateError):
            clean.validate_target(tree, UUID, '/dev/sdz1')
        tree = inventory()
        tree['blockdevices'][0]['children'].append({'path': '/dev/sdz2', 'type': 'part'})
        with self.assertRaises(clean.GateError):
            clean.validate_target(tree, UUID, '/dev/sdz1')

    def test_mount_namespace_detection_matches_exact_major_minor(self):
        clean.reject_mounted_device('8:1', ['32 1 8:10 / /other rw - ext4 /dev/other rw'])
        with self.assertRaises(clean.GateError):
            clean.reject_mounted_device('8:1', ['32 1 8:1 / /hidden rw - ext4 /dev/target rw'])

    def test_fstab_conflicts_rejected_without_overwriting_root_entries(self):
        original = 'UUID=system / ext4 defaults 0 1\n'
        clean.validate_fstab(original, UUID, '/dev/sdz1')
        for entry in [f'UUID={UUID} /old ext4 defaults 0 2', 'UUID=other /data ext4 defaults 0 2',
                      '/dev/sdz1 /old ext4 defaults 0 2', 'LABEL=HOMELAB_DATA /old ext4 defaults 0 2']:
            with self.assertRaises(clean.GateError):
                clean.validate_fstab(original + entry, UUID, '/dev/sdz1')

    def test_unprivileged_execution_never_invokes_any_command(self):
        with patch.object(clean.os, 'geteuid', return_value=1000), patch.object(clean.subprocess, 'run') as run:
            result = clean.main(UUID, 'mew')
        self.assertEqual(result['errorCode'], 'INTERACTIVE_OWNER_SUDO_REQUIRED')
        self.assertEqual(result['formatting'], 'NOT_EXECUTED')
        run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
