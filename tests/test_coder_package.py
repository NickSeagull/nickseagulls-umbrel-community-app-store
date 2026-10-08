"""Static regression checks for the Coder package (no host services started)."""
from pathlib import Path
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "nickseagull-coder"


class CoderPackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = yaml.safe_load((APP / "umbrel-app.yml").read_text())
        cls.compose = yaml.safe_load((APP / "docker-compose.yml").read_text())

    def test_manifest_and_settings(self):
        m = self.manifest
        self.assertEqual(m["id"], APP.name)
        self.assertEqual(m["storage"], {"dataRoot": "data"})
        self.assertEqual(m["version"], "2.36.7")
        self.assertEqual(m["port"], 4584)
        self.assertEqual(m["path"], "")
        self.assertFalse(m["deterministicPassword"])
        self.assertEqual(m["environment"][0]["name"], "CODER_ACCESS_URL")
        self.assertEqual(m["environment"][0]["services"], ["server"])

    def test_proxy_and_protocol_auth_boundary(self):
        services = self.compose["services"]
        proxy = services["app_proxy"]["environment"]
        self.assertEqual(proxy["APP_HOST"], "nickseagull-coder_server_1")
        self.assertEqual(proxy["APP_PORT"], 7080)
        self.assertEqual(proxy["PROXY_AUTH_WHITELIST"], "/api/*,/derp/*")
        self.assertNotIn("PROXY_AUTH_ADD", proxy)
        server = services["server"]
        self.assertEqual(server["environment"]["CODER_HTTP_ADDRESS"], "0.0.0.0:7080")
        self.assertEqual(server["environment"]["CODER_PROVISIONER_DAEMONS"], "1")
        self.assertEqual(server["environment"]["CODER_DERP_FORCE_WEBSOCKETS"], "true")
        self.assertEqual(server["environment"]["CODER_ACCESS_URL"], "http://${DEVICE_DOMAIN_NAME}:4584")
        self.assertNotIn("ports", server)

    def test_database_ssh_and_local_docker_persistence(self):
        s = self.compose["services"]
        self.assertEqual(s["server"]["depends_on"]["database"]["condition"], "service_healthy")
        self.assertIn("${APP_DATA_DIR}/data/coder:/home/coder", s["server"]["volumes"])
        self.assertIn("/var/run/docker.sock:/var/run/docker.sock", s["server"]["volumes"])
        self.assertEqual(s["server"]["group_add"], ["${APP_NICKSEAGULL_CODER_DOCKER_GID}"])
        self.assertIn("${APP_DATA_DIR}/data/ssh:/home/coder/.ssh:ro", s["server"]["volumes"])
        self.assertIn("${APP_DATA_DIR}/data/postgres:/var/lib/postgresql/data", s["database"]["volumes"])
        for d in ("coder", "ssh", "postgres"):
            self.assertTrue((APP / "data" / d / ".gitkeep").is_file())
        self.assertEqual(s["database"]["environment"]["POSTGRES_PASSWORD"], "${APP_NICKSEAGULL_CODER_DB_PASSWORD}")
        self.assertIn("${APP_NICKSEAGULL_CODER_DB_PASSWORD}", s["server"]["environment"]["CODER_PG_CONNECTION_URL"])
        self.assertIn("derive_entropy", (APP / "exports.sh").read_text())
        self.assertIn('stat -c %g /var/run/docker.sock', (APP / "exports.sh").read_text())
        for name in ("server", "database"):
            self.assertNotIn("ports", s[name])
            for disallowed in ("privileged", "cap_add", "network_mode", "security_opt"):
                self.assertNotIn(disallowed, s[name])
        self.assertEqual(sorted(p.name for p in (APP / "data" / "ssh").iterdir()), [".gitkeep"])

    def test_pinned_images(self):
        s = self.compose["services"]
        self.assertEqual(s["server"]["image"], "ghcr.io/coder/coder:v2.36.7@sha256:e8b2743529aea6a1e77bba764c8ec4a04dec65d27ca9caa0ec0b2dbcd3db0565")
        self.assertEqual(s["database"]["image"], "docker.io/library/postgres:17.6-alpine@sha256:ef257d85f76e48da1c64832459b59fcaba1a4dac97bf5d7450c77753542eee94")


if __name__ == "__main__":
    unittest.main()
