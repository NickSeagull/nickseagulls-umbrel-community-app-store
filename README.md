# NickSeagull Umbrel Community App Store

App ID prefix: `nickseagull`.

## Chromium for RAMSYS — sandboxed persistent browser

`nickseagull-chromium` pins `jlesage/chromium` 26.09.2 by multi-architecture digest. Its Umbrel tile provides a visual Chromium window backed by one persistent `/config/chromium/Default` profile, and its stock CDP listener is reachable at `nickseagull-chromium_server_1:9222` from Umbrel Docker peers. **Same-host container access is trusted** by Nick; CDP and VNC access from peers is intentional on this closed network. This app does not publish those ports on the host or Internet. The Umbrel app proxy protects the tile route, not direct peer connections.

The browser keeps the versioned AppArmor policy, scoped seccomp exceptions for Chromium namespaces, no `CAP_SYS_ADMIN`, and a launcher that cannot silently fall back to `--no-sandbox`. These are defenses against malicious web content, not a guarantee that browser vulnerabilities are impossible. A live 26.09.4 install passed `chrome://sandbox` (PID/network namespaces and Seccomp-BPF), and a harmless cookie confirmed on disk survived an Umbrel restart. Version 26.09.5's additional SSH sidecar was unnecessary for Nick's threat model and failed after an app restart; 26.09.6 removes it without changing the browser profile or sandbox policy.

### Verify after updating

1. Open the graphical Umbrel tile. Check `chrome://version` shows `/config/chromium/Default` without `--no-sandbox`; `chrome://sandbox` must report adequate sandboxing with PID/network namespaces and Seccomp-BPF.
2. From Hermes, connect directly to the shared-network `:9222` endpoint and confirm it controls the same visible browser. The `browser.cdp_url` setting should point to that service, not a local SSH tunnel.
3. Check the existing synthetic persistence-test cookie after the update, delete only that named cookie, and confirm its absence on disk. Keep Hermes cron jobs paused.

Changes to the AppArmor policy require a new profile name; a stale same-named policy can otherwise mask a swallowed pre-start hook failure. The policy is Docker-default-like rather than narrow domain confinement, and an app-store hook runs with host authority.

The manifest icon points to this repository's `master` branch; the package lives under `nickseagull-chromium/`.

## OmniRoute

`nickseagull-omniroute` packages the upstream OmniRoute 3.8.51 multi-architecture Docker image and a private Redis sidecar. Both images are pinned by tag and image-index digest. App data and Redis state are bind-mounted under the app's movable `data/` root. The dashboard opens behind Umbrel login; OmniRoute also requires its own dashboard password, initialized from the Umbrel-displayed app password. If that password is subsequently changed inside OmniRoute, Umbrel's displayed initial password will no longer be current.

Clients use the Umbrel app origin at `/v1` with an **OmniRoute API key created in its dashboard**. Only `/v1/*` bypasses the Umbrel browser-cookie check; OmniRoute's own `REQUIRE_API_KEY=true` remains enforced. Do not share the password or API keys. The app does not expose Redis or mount the Docker socket, host CLI credentials, or browser profiles. Do not enable upstream fingerprint/header spoofing or use account rotation to bypass subscription limits. Use separately authorized provider credentials; TypeSafe Jev remains a direct, separate API integration rather than an OmniRoute chat-model route.

The package has static validation and image-architecture checks but has **not** been installed through Umbrel or tested for browser login, authenticated client requests, restart persistence, or OAuth callbacks. The recommended first smoke test is a fresh Umbrel install, dashboard sign-in, creation of a test API key, a `/v1/models` call through the Umbrel proxy, restart, then a repeat login/request without losing config. Do not point production agents at the app until that passes.

## Home Assistant Matter Hub

`nickseagull-matter-hub` packages the maintained RiDDiX fork v2.0.58 (not the archived t0bst4r image). Unlike Umbrel's Matter Server, it exports HA entities *out* to a Google Matter hub. Its container uses host networking for Matter's IPv6/mDNS commissioning; its web UI listens on host port 8482 and requires HTTP Basic auth (`admin`, Umbrel's generated app password). The UI is directly reachable on the LAN, not solely via Umbrel's app proxy. Avoid publishing 8482 to the Internet. HA stays at `127.0.0.1:8123` on the shared host network. Persistent fabric/bridge state is under `data/state`.

**Before installation:** create `${APP_DATA_DIR}/ha.env` in this app's fixed host definition directory (normally `~/umbrel/app-data/nickseagull-matter-hub/ha.env`) with one line `HAMH_HOME_ASSISTANT_ACCESS_TOKEN=<your HA long-lived access token>` and mode 600. This credential remains in the fixed definition directory when Umbrel moves the app's `data/` storage root. Never commit or paste that token into a PR. The Compose package requires this file; if missing, installation fails rather than starting a nonfunctional bridge. Umbrel's Home Assistant app must already be installed. The token grants broad HA access: secure backups and revoke it if compromised.

After install, open Matter Hub at port 8482, authenticate with the app password, create a bridge that filters to only the intended entities (start with a single light), then pair its QR code in Google Home. Google needs a compatible Matter hub on the LAN. Verify actual state/control in both Google Home and HA before expanding the exposed set. The package does not auto-expose all entities or send any physical device command at installation.
