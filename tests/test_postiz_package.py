"""Static install-safety checks; run with: uv run --with pyyaml python test_package.py."""
from pathlib import Path
import re
import unittest
import yaml

ROOT = Path(__file__).resolve().parent.parent / 'nickseagull-postiz'


class PostizPackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.compose_text = (ROOT / 'docker-compose.yml').read_text()
        cls.compose = yaml.safe_load(cls.compose_text)
        cls.manifest = yaml.safe_load((ROOT / 'umbrel-app.yml').read_text())
        cls.services = cls.compose['services']

    def test_release_identity_and_pinned_image(self):
        self.assertEqual(self.manifest['id'], 'nickseagull-postiz')
        self.assertEqual(self.manifest['version'], '2.26.0')
        self.assertEqual(self.services['postiz']['image'],
                         'ghcr.io/gitroomhq/postiz-app:v2.26.0@sha256:875e61ac5d0ac43c3dec78a78a7032dfb03d9a8c6d4936ebb18adb606cc207c5')
        self.assertNotIn('v2.21.10', self.compose_text)
        self.assertEqual(self.manifest['storage']['dataRoot'], 'data')
        self.assertTrue((ROOT / 'data' / '.gitkeep').exists())

    def test_proxy_and_network(self):
        proxy = self.services['app_proxy']
        self.assertEqual(proxy['environment']['APP_HOST'], 'nickseagull-postiz_postiz_1')
        self.assertEqual(proxy['environment']['APP_PORT'], 5000)
        self.assertEqual(self.manifest['port'], 4677)
        self.assertEqual(proxy['depends_on']['postiz']['condition'], 'service_healthy')
        for name, svc in self.services.items():
            if name != 'app_proxy':
                self.assertNotIn('ports', svc, name)
                self.assertNotIn('privileged', svc, name)
                self.assertNotIn('network_mode', svc, name)
                self.assertNotIn('security_opt', svc, name)
                self.assertNotIn('cap_add', svc, name)

    def test_secrets_and_storage(self):
        app = self.services['postiz']
        env = app['environment']
        self.assertEqual(env['JWT_SECRET'], '${APP_SEED}')
        self.assertIn('${APP_SEED}', env['DATABASE_URL'])
        self.assertEqual(self.services['postgres']['environment']['POSTGRES_PASSWORD'], '${APP_SEED}')
        self.assertEqual(self.services['temporal-postgres']['environment']['POSTGRES_PASSWORD'], '${APP_SEED}')
        self.assertEqual(self.services['temporal']['environment']['POSTGRES_PWD'], '${APP_SEED}')
        self.assertEqual(env['BACKEND_INTERNAL_URL'], 'http://localhost:3000')
        self.assertEqual(env['TEMPORAL_ADDRESS'], 'temporal:7233')
        self.assertEqual(env['STORAGE_PROVIDER'], 'local')
        self.assertEqual(self.services['permissions']['restart'], 'no')
        self.assertEqual(self.services['temporal']['depends_on']['temporal-elasticsearch']['condition'], 'service_healthy')
        for name, svc in self.services.items():
            for mount in svc.get('volumes', []):
                self.assertTrue(mount.startswith('${APP_DATA_DIR}/data:' ) or mount.startswith('${APP_DATA_DIR}/data/'), (name, mount))
                self.assertNotIn('docker.sock', mount)
        self.assertNotIn('ENCRYPTION_PROVIDER:', self.compose_text)
        self.assertNotIn('ENCRYPTION_KEY:', self.compose_text)

    def test_urls_and_dependency_versions(self):
        env = self.services['postiz']['environment']
        for key in ('MAIN_URL', 'FRONTEND_URL', 'BACKEND_URL', 'NEXT_PUBLIC_BACKEND_URL'):
            self.assertIn('${DEVICE_DOMAIN_NAME}:4677', env[key])
        self.assertEqual(env['NEXT_PUBLIC_OVERRIDE_BACKEND_URL'], '/api')
        for name, prefix in {'postgres': 'postgres:17-', 'redis': 'redis:7.2-',
                             'temporal': 'temporalio/auto-setup:1.28.1',
                             'temporal-postgres': 'postgres:16-',
                             'temporal-elasticsearch': 'elasticsearch:7.17.27'}.items():
            self.assertTrue(self.services[name]['image'].startswith(prefix), name)


if __name__ == '__main__':
    unittest.main()
