# NickSeagull Umbrel Community App Store

App ID prefix: `nickseagull`.

## Chromium for RAMSYS — unsigned-in private-CDP experiment

`nickseagull-chromium` pins `jlesage/chromium` 26.09.2 by multi-architecture digest. Its Umbrel app tile opens a visual browser with a persistent `/config` profile. Version 26.09.4 passed a live sandbox self-check, CDP handshake, and synthetic-cookie persistence across an Umbrel restart, but **26.09.4 exposed unauthenticated CDP** to the shared Docker network. **Do not sign in to GitHub, Gmail, or other real accounts yet.** Umbrel's visual app proxy does not protect raw CDP.

The existing browser-specific AppArmor policy, seccomp profile, no-`CAP_SYS_ADMIN` setup, and fail-closed launcher remain unchanged. Version 26.09.5 is an **untested access-control candidate**: disable the image's network-wide `socat` debugging proxy, request Chromium CDP on container loopback, and add a pinned OpenSSH sidecar sharing the browser's network namespace. Only a dedicated Hermes public key is allowed to forward to `127.0.0.1:9222`; shell sessions, passwords, sudo and other forwards are disabled. The private key stays under Hermes' persistent `/opt/data`, never in this repository; SSH host keys persist in the app's `data/cdp-ssh` directory. The package ships only a public key and SSH restrictions under update-copied `hooks/`. The sidecar copies the policy into its persistent config at startup and refuses SSH service if the effective policy or public key is missing, avoiding a read-only mount beneath LinuxServer's recursively owned `/config`.

### Experimental update and acceptance (unsigned-in)

1. Update **Chromium for RAMSYS** in Umbrel. Verify the graphical window and `chrome://sandbox` remain functional, with `/config/chromium/Default` as the profile and no `--no-sandbox` flag.
2. Prove unauthenticated raw CDP on the browser container's shared-network IP port 9222 is **unreachable**. Prove wrong-key SSH and shell sessions fail; the pinned-key SSH tunnel must reach only loopback CDP and control the same visually displayed browser.
3. Restart the app and Hermes independently. Check tunnel reconnection, adequate sandboxing and synthetic cookie persistence across app restart (wait until the expiring cookie is confirmed on disk before restarting), then delete the named probe cookie and verify its absence.

**No real-account sign-in until raw CDP is unreachable and the authenticated tunnel, browser sandbox, and restart paths pass live checks.** Changes to the AppArmor policy require a new profile name; a stale same-named policy can otherwise mask a swallowed pre-start hook failure. The policy is Docker-default-like rather than narrow domain confinement, and an app-store hook runs with host authority. Keep Hermes cron jobs paused.

The manifest icon points to this repository's `master` branch; the package lives under `nickseagull-chromium/`.

## OmniRoute

`nickseagull-omniroute` packages the upstream OmniRoute 3.8.51 multi-architecture Docker image and a private Redis sidecar. Both images are pinned by tag and image-index digest. App data and Redis state are bind-mounted under the app's movable `data/` root. The dashboard opens behind Umbrel login; OmniRoute also requires its own dashboard password, initialized from the Umbrel-displayed app password. If that password is subsequently changed inside OmniRoute, Umbrel's displayed initial password will no longer be current.

Clients use the Umbrel app origin at `/v1` with an **OmniRoute API key created in its dashboard**. Only `/v1/*` bypasses the Umbrel browser-cookie check; OmniRoute's own `REQUIRE_API_KEY=true` remains enforced. Do not share the password or API keys. The app does not expose Redis or mount the Docker socket, host CLI credentials, or browser profiles. Do not enable upstream fingerprint/header spoofing or use account rotation to bypass subscription limits. Use separately authorized provider credentials; TypeSafe Jev remains a direct, separate API integration rather than an OmniRoute chat-model route.

The package has static validation and image-architecture checks but has **not** been installed through Umbrel or tested for browser login, authenticated client requests, restart persistence, or OAuth callbacks. The recommended first smoke test is a fresh Umbrel install, dashboard sign-in, creation of a test API key, a `/v1/models` call through the Umbrel proxy, restart, then a repeat login/request without losing config. Do not point production agents at the app until that passes.
