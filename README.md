# NickSeagull Umbrel Community App Store

App ID prefix: `nickseagull`.

## Chromium for RAMSYS

`nickseagull-chromium` packages the upstream `jlesage/chromium` image, pinned to release 26.09.2 and its multi-architecture image-index digest. It runs **one persistent visual Chromium browser**. Nick signs in through the Umbrel app tile; RAMSYS can attach to that same browser through CDP at `nickseagull-chromium_server_1:9222` on the Umbrel Docker network. The browser's state is stored in the app's `data` directory, mounted to `/config`. The web terminal and file manager remain off. Browserless is a separate disposable-session tool and is not part of this app.

The app uses a vendored Docker v28.5.1 default seccomp profile with only `unshare` additionally allowed so Chromium can attempt its renderer sandbox without privileged mode or `SYS_ADMIN`. Source: `moby/moby` at `v28.5.1/vendor/github.com/moby/profiles/seccomp/default.json`; the vendored profile is under Moby's Apache-2.0 license (`nickseagull-chromium/SECCOMP-LICENSE`). **Runtime sandbox status has not been tested on Umbrel**; inspect `chrome://sandbox` before signing into accounts. The image's CDP implementation is documented upstream. An app manifest alone does not prove that the Umbrel app proxy or CDP connection works on Nick's host.

### Installation and acceptance

1. Add this repository as a Community App Store in umbrelOS; install **Chromium for RAMSYS**. Do not uninstall the existing Browserless app as part of this test.
2. Open its app tile and check that the graphical Chromium window loads. Inspect `chrome://version` for a profile path under `/config`; inspect `chrome://sandbox` for actual sandbox status.
3. From Hermes, check the app's CDP `/json/version` and connect via WebSocket. The browser displayed in the app tile and the CDP target must be the same instance.
4. Set a *synthetic expiring* cookie on a harmless test origin. Restart **only this browser app**, reconnect, read the cookie back, then delete it. A cookie visible only in the same session is insufficient evidence of persistence.
5. Only after those checks should Nick sign into web apps himself. Configure the active RAMSYS browser endpoint separately; do not transfer corthan credentials or resume cron jobs.

The manifest's icon points to this repository's `master` branch; it becomes available after the app change is merged. The app's package files live under `nickseagull-chromium/`.
