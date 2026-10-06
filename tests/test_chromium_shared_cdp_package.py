"""Contract for the browser CDP route Nick accepts on his closed Umbrel network."""
from pathlib import Path
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "nickseagull-chromium"

class SharedCdpPackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.compose = yaml.safe_load((APP / "docker-compose.yml").read_text())
        cls.manifest = yaml.safe_load((APP / "umbrel-app.yml").read_text())

    def test_browser_exposes_stock_cdp_to_same_host_docker_peers(self):
        services = self.compose["services"]
        self.assertEqual(set(services), {"app_proxy", "server"})
        server = services["server"]
        self.assertEqual(server["environment"]["CHROMIUM_REMOTE_DEBUGGING"], "1")
        self.assertNotIn("CHROMIUM_CUSTOM_ARGS", server["environment"])
        self.assertNotIn("ports", server)  # No host/LAN publication.
        self.assertEqual(self.compose["services"]["app_proxy"]["environment"]["APP_PORT"], 5800)

    def test_sandbox_and_persistent_visual_profile_remain_required(self):
        server = self.compose["services"]["server"]
        self.assertIn("${APP_DATA_DIR}/data:/config:rw", server["volumes"])
        self.assertIn("${APP_DATA_DIR}/hooks/params-sandbox-required:/etc/services.d/app/params:ro", server["volumes"])
        self.assertTrue(any(str(o).startswith("seccomp:${APP_DATA_DIR}/hooks/seccomp.json") for o in server["security_opt"]))
        self.assertTrue(any(str(o).startswith("apparmor=nickseagull-chromium-") for o in server["security_opt"]))
        self.assertNotIn("cap_add", server)

    def test_remove_unneeded_ssh_identity_and_bump_version(self):
        self.assertEqual(self.manifest["version"], "26.09.6")
        self.assertFalse(list((APP / "hooks").glob("cdp-*")))
        self.assertIn("Same-host container access is trusted", (ROOT / "README.md").read_text())

if __name__ == "__main__":
    unittest.main()
