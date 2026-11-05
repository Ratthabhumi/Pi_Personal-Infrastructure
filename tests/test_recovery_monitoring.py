import copy
import importlib.util
import os
from pathlib import Path
import unittest
from unittest.mock import patch

if os.name == 'posix':
    spec = importlib.util.spec_from_file_location('finish', Path(__file__).resolve().parents[1] / 'scripts/recovery/finish_monitoring.py')
    finish = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(finish)


def container():
    return {'Config': {'Image': 'prom/node-exporter:v1.8.2', 'User': '65534:65534',
                       'Cmd': ['--web.listen-address=127.0.0.1:9100']},
            'State': {'Running': True, 'OOMKilled': False},
            'HostConfig': {'ReadonlyRootfs': True, 'Memory': 64 * 1024 * 1024,
                           'PidsLimit': 64, 'NanoCpus': 250000000,
                           'SecurityOpt': ['no-new-privileges:true'], 'CapDrop': ['ALL'],
                           'NetworkMode': 'host', 'PortBindings': {}}}


@unittest.skipUnless(os.name == 'posix', 'Linux monitoring repair')
class MonitoringFinish(unittest.TestCase):
    def test_repair_requires_proven_healthy_internal_exporter_and_exact_profile(self):
        self.assertEqual(finish.classify(False, True, True, True, True), 'HEALTHY_EXPORTER_UNREACHABLE_HOST_BRIDGE_PUBLICATION')
        for conditions in [(False,False,True,True,True), (False,True,False,True,True),
                           (False,True,True,False,True), (False,True,True,True,False)]:
            self.assertEqual(finish.classify(*conditions), 'UNPROVEN_CAUSE_NO_REPAIR')
        self.assertEqual(finish.classify(True, False, True, True, True), 'ALREADY_HEALTHY')

    def test_new_profile_runtime_limits_and_loopback_are_enforced(self):
        finish.validate_container(container(), host_network=True)
        for key, value in [('Memory', 0), ('ReadonlyRootfs', False), ('PidsLimit', 0),
                           ('NanoCpus', 0), ('CapDrop', []), ('SecurityOpt', []),
                           ('NetworkMode', 'bridge'), ('PortBindings', {'9100/tcp': [{}]})]:
            c = copy.deepcopy(container()); c['HostConfig'][key] = value
            with self.assertRaises(finish.Blocked, msg=key):
                finish.validate_container(c, host_network=True)
        c = container(); c['Config']['Cmd'] = ['--web.listen-address=0.0.0.0:9100']
        with self.assertRaises(finish.Blocked): finish.validate_container(c, host_network=True)

    def test_metrics_body_requires_both_host_cpu_and_memory(self):
        self.assertTrue(finish.metrics('node_cpu_seconds_total 1\nnode_memory_MemTotal_bytes 100'))
        self.assertFalse(finish.metrics('node_cpu_seconds_total 1'))
        self.assertFalse(finish.metrics('HTTP OK'))

    def test_nonroot_never_runs_commands_or_changes_profile(self):
        with patch.object(finish.os, 'geteuid', return_value=1000), patch.object(finish.subprocess, 'run') as run:
            report = finish.main('11111111-1111-1111-1111-111111111111')
        self.assertEqual(report['errorCode'], 'INTERACTIVE_OWNER_SUDO_REQUIRED')
        self.assertEqual(report['repairAttempts'], 0)
        run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
