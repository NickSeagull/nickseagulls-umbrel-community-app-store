"""Contract for an unsigned-in, authenticated CDP tunnel in the Umbrel app."""
from pathlib import Path
import unittest
import yaml

APP = Path(__file__).resolve().parents[1] / "nickseagull-chromium"


class PrivateCdpPackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.compose = yaml.safe_load((APP / "docker-compose.yml").read_text())

    def test_stock_unauthenticated_socat_listener_is_disabled(self):
        server = self.compose["services"]["server"]
        self.assertEqual(server["environment"]["CHROMIUM_REMOTE_DEBUGGING"], "0")
        args = server["environment"]["CHROMIUM_CUSTOM_ARGS"]
        self.assertIn("--remote-debugging-port=9222", args)
        self.assertIn("--remote-debugging-address=127.0.0.1", args)
        self.assertNotIn("ports", server)

    def test_ssh_sidecar_only_shares_browser_network_namespace(self):
        ssh = self.compose["services"]["cdp_ssh"]
        self.assertEqual(ssh["network_mode"], "service:server")
        self.assertEqual(ssh["depends_on"]["server"]["restart"], True)
        self.assertNotIn("ports", ssh)
        self.assertNotIn("privileged", ssh)
        self.assertNotIn("cap_add", ssh)
        self.assertIn("@sha256:", ssh["image"])
        self.assertEqual(ssh["environment"]["PASSWORD_ACCESS"], "false")
        self.assertEqual(ssh["environment"]["SUDO_ACCESS"], "false")
        self.assertNotIn("PUBLIC_KEY", ssh["environment"])
        self.assertNotIn("PUBLIC_KEY_FILE", ssh["environment"])
        self.assertIn("${APP_DATA_DIR}/data/cdp-ssh:/config:rw", ssh["volumes"])
        self.assertIn("${APP_DATA_DIR}/hooks/cdp-client.pub:/key/ramsys.pub:ro", ssh["volumes"])
        self.assertIn("${APP_DATA_DIR}/hooks/cdp-sshd.conf:/key/cdp-sshd.conf:ro", ssh["volumes"])
        self.assertIn("${APP_DATA_DIR}/hooks/cdp-entrypoint:/usr/local/bin/cdp-entrypoint:ro", ssh["volumes"])
        self.assertIn("${APP_DATA_DIR}/hooks/cdp-sshd-run:/etc/s6-overlay/s6-rc.d/svc-openssh-server/run:ro", ssh["volumes"])
        self.assertEqual(ssh["entrypoint"], ["/bin/sh", "/usr/local/bin/cdp-entrypoint"])

    def test_sidecar_fails_closed_if_policy_is_missing_or_not_effective(self):
        entrypoint = (APP / "hooks" / "cdp-entrypoint").read_text()
        run = (APP / "hooks" / "cdp-sshd-run").read_text()
        self.assertIn("/key/cdp-sshd.conf", entrypoint)
        self.assertIn("rm -rf /config/sshd", entrypoint)
        self.assertIn("/config/sshd/sshd_config.d/10-cdp-only.conf", entrypoint)
        self.assertIn("/key/ramsys.pub", entrypoint)
        self.assertIn("exec /init", entrypoint)
        self.assertIn("sshd.pam -T", run)
        self.assertIn("authorizedkeysfile /key/ramsys.pub", run)
        self.assertIn("allowtcpforwarding local", run)
        self.assertIn("permitopen 127.0.0.1:9222", run)
        self.assertIn("maxsessions 0", run)

    def test_ssh_server_forwards_only_to_loopback_cdp_without_shell(self):
        config = (APP / "hooks" / "cdp-sshd.conf").read_text()
        for rule in (
            "AuthorizedKeysFile /key/ramsys.pub",
            "AllowUsers cdp",
            "AuthenticationMethods publickey",
            "PasswordAuthentication no",
            "KbdInteractiveAuthentication no",
            "PermitRootLogin no",
            "AllowTcpForwarding local",
            "PermitOpen 127.0.0.1:9222",
            "MaxSessions 0",
            "PermitTTY no",
            "X11Forwarding no",
            "AllowAgentForwarding no",
        ):
            self.assertIn(rule, config)
        pubkey = (APP / "hooks" / "cdp-client.pub").read_text()
        self.assertTrue(pubkey.startswith("ssh-ed25519 "))
        self.assertEqual(len(pubkey.splitlines()), 1)


if __name__ == "__main__":
    unittest.main()
