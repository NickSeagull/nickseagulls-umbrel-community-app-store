"""Package-contract checks that run without a Minecraft daemon or Playit account."""
import importlib.util
from importlib.machinery import SourceFileLoader
import os
from pathlib import Path
import socket
import threading
import unittest
import urllib.request
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[1] / "nickseagull-prominence-ii"


class PackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text())
        cls.manifest = yaml.safe_load((ROOT / "umbrel-app.yml").read_text())

    def test_manifest_and_wiring(self):
        m, services = self.manifest, self.compose["services"]
        self.assertEqual(m["id"], ROOT.name)
        self.assertEqual(m["storage"], {"dataRoot": "data"})
        self.assertEqual(services["app_proxy"]["environment"], {"APP_HOST": "nickseagull-prominence-ii_status_1", "APP_PORT": 8080})
        self.assertEqual(m["port"], 4584)
        self.assertTrue((ROOT / "status.py.template").is_file())
        self.assertFalse((ROOT / "status.py").exists())
        for directory in ("minecraft", "curseforge-downloads"):
            self.assertTrue((ROOT / "data" / directory / ".gitkeep").is_file())
        settings = {(s["name"], tuple(s["services"])) for s in m["environment"]}
        for service, key in (("server", "EULA"), ("server", "WHITELIST"),
                             ("server", "CF_FILE_ID"), ("playit", "SECRET_KEY")):
            self.assertIn((key, (service,)), settings)
            self.assertIn(key, services[service]["environment"])

    def test_private_fail_closed_defaults(self):
        services = self.compose["services"]
        env = services["server"]["environment"]
        self.assertEqual(env["EULA"], "TRUE")
        self.assertEqual(env["MODPACK_PLATFORM"], "AUTO_CURSEFORGE")
        self.assertEqual(env["CF_FILE_ID"], "9094769")
        self.assertEqual(env["ENABLE_WHITELIST"], "TRUE")
        self.assertEqual(env["ONLINE_MODE"], "TRUE")
        self.assertEqual(env["EXISTING_WHITELIST_FILE"], "SYNCHRONIZE")
        self.assertEqual(services["playit"]["environment"]["SECRET_KEY"], "${PLAYIT_SECRET_KEY:-}")
        self.assertEqual(services["playit"]["network_mode"], "service:server")
        self.assertFalse(any("ports" in svc or "privileged" in svc for svc in services.values()))
        self.assertTrue(any(v.endswith("/data/minecraft:/data") for v in services["server"]["volumes"]))
        self.assertTrue(any(v.endswith("/data/curseforge-downloads:/downloads") for v in services["server"]["volumes"]))

    def test_status_page_offline_and_online(self):
        source = ROOT / "status.py.template"
        spec = importlib.util.spec_from_loader("prominence_status", SourceFileLoader("prominence_status", str(source)))
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        from http.server import ThreadingHTTPServer
        with ThreadingHTTPServer(("127.0.0.1", 0), module.Handler) as http:
            thread = threading.Thread(target=http.serve_forever, daemon=True)
            thread.start()
            url = f"http://127.0.0.1:{http.server_port}/"
            with urllib.request.urlopen(url) as response:
                self.assertIn("Not listening yet", response.read().decode())
            with socket.socket() as mc:
                mc.bind(("127.0.0.1", 0))
                mc.listen(1)
                with patch.object(module, "HOST", "127.0.0.1"), patch.object(module, "PORT", mc.getsockname()[1]):
                    with urllib.request.urlopen(url) as response:
                        self.assertIn("Listening on the private app network", response.read().decode())
                    with urllib.request.urlopen(url + "health") as response:
                        self.assertEqual(response.read(), b"ok\n")
            http.shutdown()
            thread.join(timeout=3)


if __name__ == "__main__":
    unittest.main()
