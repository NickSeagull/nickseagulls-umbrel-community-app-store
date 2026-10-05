# NickSeagull Umbrel Community App Store

App ID prefix: `nickseagull`.

## Chromium for RAMSYS — unsigned-in sandbox experiment

`nickseagull-chromium` pins `jlesage/chromium` 26.09.2 by multi-architecture digest. It provides one visual Chromium process and a CDP endpoint at `nickseagull-chromium_server_1:9222` on the Umbrel Docker network, with a persistent `/config` volume. The web terminal and file manager are disabled. **Do not sign in to GitHub, Gmail, or other real accounts yet.** CDP is currently unauthenticated on the internal Docker network; Umbrel's visual app proxy does not protect that endpoint.

This revision removes `CAP_SYS_ADMIN`. A versioned, Docker-28.5.0-derived AppArmor profile (Apache-2.0) adds `userns create,` while retaining Docker-default-style denials. An Umbrel `hooks/pre-start` attempts to load it on the host; Compose requires the named enforcing policy. The custom Docker-default-derived seccomp profile (Apache-2.0; `SECCOMP-LICENSE`) allows the user- and PID-namespace `clone` calls needed by Chromium and is stored under `hooks/` because Umbrel copies that directory on app updates. A read-only adaptation of upstream's launcher parameters (MIT; `PARAMS-LICENSE`) omits its `--no-sandbox` fallback. The startup guard checks its AppArmor label and seccomp mode, but **does not by itself prove renderer isolation or the exact seccomp filter**. App store updates that change the AppArmor policy must also change its profile name; otherwise a previously loaded same-named policy could mask a failed hook reload.

An **unsigned-in direct Docker probe** on Nick's Umbrel passed `chrome://sandbox` with PID/network namespaces and Seccomp-BPF active, visual HTTP and CDP, and a harmless persistent cookie across a container restart. That cookie was deleted and its absence verified. The packaged Umbrel install/update path has **not** passed a live test, and the AppArmor policy is Docker-default-like rather than domain-specific confinement. Loading it through an upstream host-root pre-start hook is a material supply-chain/security boundary; the installed lifecycle has not been exercised.

### Experimental installation and acceptance (no account sign-in)

1. Refresh this Community App Store and update **Chromium for RAMSYS** if it is installed, or install it if absent. Do not uninstall Browserless as part of this test.
2. Check that the app tile opens the graphical window, `chrome://version` has a profile path under `/config` without `--no-sandbox`, and `chrome://sandbox` reports adequate sandboxing with PID/network namespaces and Seccomp-BPF active.
3. Check CDP `/json/version` and a WebSocket browser connection from Hermes, then set an expiring synthetic cookie on a harmless origin. Restart **only this app**, read the cookie back, and delete it. A fresh CDP connection alone is not a restart test.
4. Test an app update and a failed policy-load path before treating the AppArmor hook as reliable. Design and verify authenticated/controlled CDP access before using this app for sensitive signed-in sessions. Keep Hermes cron jobs paused.

The manifest icon points to this repository's `master` branch; the package lives under `nickseagull-chromium/`.

## OmniRoute

`nickseagull-omniroute` packages the upstream OmniRoute 3.8.51 multi-architecture Docker image and a private Redis sidecar. Both images are pinned by tag and image-index digest. App data and Redis state are bind-mounted under the app's movable `data/` root. The dashboard opens behind Umbrel login; OmniRoute also requires its own dashboard password, initialized from the Umbrel-displayed app password. If that password is subsequently changed inside OmniRoute, Umbrel's displayed initial password will no longer be current.

Clients use the Umbrel app origin at `/v1` with an **OmniRoute API key created in its dashboard**. Only `/v1/*` bypasses the Umbrel browser-cookie check; OmniRoute's own `REQUIRE_API_KEY=true` remains enforced. Do not share the password or API keys. The app does not expose Redis or mount the Docker socket, host CLI credentials, or browser profiles. Do not enable upstream fingerprint/header spoofing or use account rotation to bypass subscription limits. Use separately authorized provider credentials; TypeSafe Jev remains a direct, separate API integration rather than an OmniRoute chat-model route.

The package has static validation and image-architecture checks but has **not** been installed through Umbrel or tested for browser login, authenticated client requests, restart persistence, or OAuth callbacks. The recommended first smoke test is a fresh Umbrel install, dashboard sign-in, creation of a test API key, a `/v1/models` call through the Umbrel proxy, restart, then a repeat login/request without losing config. Do not point production agents at the app until that passes.
