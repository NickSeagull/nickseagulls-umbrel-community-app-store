"""Regression checks for the intentionally narrow OmniRoute Umbrel package."""
from pathlib import Path
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "nickseagull-omniroute"


class OmniRoutePackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = yaml.safe_load((APP / "umbrel-app.yml").read_text())
        cls.compose = yaml.safe_load((APP / "docker-compose.yml").read_text())
        cls.exports = (APP / "exports.sh").read_text()

    def test_manifest_is_launchable_and_exposes_its_real_password(self):
        m = self.manifest
        self.assertEqual(m["id"], APP.name)
        self.assertEqual(m["storage"], {"dataRoot": "data"})
        self.assertEqual(m["port"], 4581)
        self.assertTrue(m["deterministicPassword"])
        self.assertEqual(m["defaultUsername"], "")
        self.assertEqual(m["path"], "")

    def test_api_only_bypasses_umbrel_cookie_gate_with_upstream_auth_enabled(self):
        services = self.compose["services"]
        proxy = services["app_proxy"]["environment"]
        self.assertEqual(proxy["APP_HOST"], "nickseagull-omniroute_server_1")
        self.assertEqual(proxy["APP_PORT"], 20128)
        self.assertEqual(proxy["PROXY_AUTH_WHITELIST"], "/v1/*")
        app = services["server"]
        self.assertEqual(app["environment"]["REQUIRE_API_KEY"], "true")
        self.assertEqual(app["environment"]["INITIAL_PASSWORD"], "${APP_PASSWORD}")
        self.assertNotIn("ports", app)
        self.assertNotIn("privileged", app)
        self.assertNotIn("cap_add", app)
        self.assertNotIn("security_opt", app)
        self.assertNotIn("/var/run/docker.sock", (APP / "docker-compose.yml").read_text())

    def test_persistent_and_private_data_is_bound_under_umbrel_data_root(self):
        s = self.compose["services"]
        self.assertIn("${APP_DATA_DIR}/data/omniroute:/app/data", s["server"]["volumes"])
        self.assertIn("${APP_DATA_DIR}/data/redis:/data", s["redis"]["volumes"])
        self.assertNotIn("ports", s["redis"])
        self.assertIn("--requirepass", s["redis"]["command"])
        self.assertIn("${APP_OMNIROUTE_REDIS_PASSWORD}", s["redis"]["command"])
        self.assertIn("${APP_OMNIROUTE_REDIS_PASSWORD}", s["server"]["environment"]["REDIS_URL"])
        self.assertIn("derive_entropy", self.exports)
        self.assertNotIn("APP_PASSWORD", self.exports)

    def test_images_are_immutable_and_upstream_stable(self):
        for name in ("server", "redis"):
            self.assertIn("@sha256:", self.compose["services"][name]["image"])
        self.assertEqual(self.manifest["version"], "3.8.51")


if __name__ == "__main__":
    unittest.main()
