"""Static fail-closed checks for the experimental Chromium AppArmor package."""
import json
from pathlib import Path
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "nickseagull-chromium"
PROFILE_NAME = "nickseagull-chromium-docker28_5_0-userns-260904"


class ChromiumAppArmorPackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.compose = yaml.safe_load((APP / "docker-compose.yml").read_text())
        cls.manifest = yaml.safe_load((APP / "umbrel-app.yml").read_text())

    def test_compose_requires_scoped_profile_and_keeps_default_denials(self):
        server = self.compose["services"]["server"]
        self.assertIn(f"apparmor={PROFILE_NAME}", server["security_opt"])
        self.assertNotIn("apparmor=unconfined", server["security_opt"])
        self.assertNotIn("seccomp=unconfined", server["security_opt"])
        self.assertNotIn("privileged", server)
        profile = (APP / "hooks" / "chromium.apparmor").read_text()
        self.assertIn(f"profile {PROFILE_NAME} ", profile)
        self.assertIn("userns create,", profile)
        self.assertIn("deny mount,", profile)

    def test_pre_start_hook_loads_exact_packaged_profile_before_compose(self):
        hook = APP / "hooks" / "pre-start"
        self.assertTrue(hook.stat().st_mode & 0o111)
        script = hook.read_text()
        self.assertIn("/usr/sbin/apparmor_parser", script)
        self.assertIn("chromium.apparmor", script)
        self.assertNotIn("apparmor=unconfined", script)

    def test_browser_starts_only_with_enforcing_profile_and_seccomp(self):
        server = self.compose["services"]["server"]
        self.assertEqual(server["entrypoint"], ["/bin/sh", "/usr/local/bin/verify-sandbox"])
        self.assertIn("${APP_DATA_DIR}/hooks/verify-sandbox:/usr/local/bin/verify-sandbox:ro", server["volumes"])
        script = (APP / "hooks" / "verify-sandbox").read_text()
        self.assertIn("/proc/self/attr/current", script)
        self.assertIn(PROFILE_NAME, script)
        self.assertIn("(enforce)", script)
        self.assertIn("/proc/self/status", script)
        self.assertIn("exec /init", script)

    def test_no_sys_admin_and_only_chromium_namespace_clone_seccomp_exceptions(self):
        server = self.compose["services"]["server"]
        self.assertNotIn("SYS_ADMIN", server.get("cap_add", []))
        self.assertIn("seccomp:${APP_DATA_DIR}/hooks/seccomp.json", server["security_opt"])
        self.assertFalse((APP / "seccomp.json").exists(), "Umbrel updates copy hooks/, not a root seccomp.json")
        profile = json.loads((APP / "hooks" / "seccomp.json").read_text())
        for flag in (268435456, 536870912):  # CLONE_NEWUSER, CLONE_NEWPID
            self.assertTrue(any(
                rule.get("names") == ["clone"]
                and rule.get("action") == "SCMP_ACT_ALLOW"
                and any(arg.get("value") == flag and arg.get("valueTwo") == flag
                        and arg.get("op") == "SCMP_CMP_MASKED_EQ" for arg in rule.get("args", []))
                for rule in profile["syscalls"]
            ), f"Missing namespace clone exception: {flag}")

    def test_launcher_never_falls_back_to_no_sandbox(self):
        server = self.compose["services"]["server"]
        self.assertIn("${APP_DATA_DIR}/hooks/params-sandbox-required:/etc/services.d/app/params:ro", server["volumes"])
        params = (APP / "hooks" / "params-sandbox-required").read_text()
        self.assertNotIn('printf "%s\\n" "--no-sandbox"', params)
        self.assertIn('"--user-data-dir=/config/chromium"', params)
        self.assertIn('CHROMIUM_REMOTE_DEBUGGING', params)

    def test_manifest_warnings_and_persistent_profile(self):
        self.assertIn("${APP_DATA_DIR}/data:/config:rw", self.compose["services"]["server"]["volumes"])
        self.assertIn("do not sign in", self.manifest["description"].lower())
        self.assertNotIn("--no-sandbox", (APP / "docker-compose.yml").read_text())


    def test_readme_cannot_invite_sensitive_sign_in_before_cdp_control(self):
        chromium_section = (ROOT / "README.md").read_text().split("## OmniRoute", 1)[0]
        self.assertIn("Do not sign in to GitHub, Gmail", chromium_section)
        self.assertIn("CDP is currently unauthenticated", chromium_section)
        self.assertNotIn("Only after those checks should Nick sign into web apps", chromium_section)
        self.assertNotIn("This packaging revision adds `SYS_ADMIN`", chromium_section)

if __name__ == "__main__":
    unittest.main()
