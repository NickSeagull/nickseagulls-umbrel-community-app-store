# NickSeagull Umbrel Community App Store

App ID prefix: `nickseagull`.

## Chromium for RAMSYS

`nickseagull-chromium` packages the upstream `jlesage/chromium` image, pinned to release 26.09.2 and its multi-architecture image-index digest. It runs **one persistent visual Chromium browser**. Nick signs in through the Umbrel app tile; RAMSYS can attach to that same browser through CDP at `nickseagull-chromium_server_1:9222` on the Umbrel Docker network. The browser's state is stored in the app's `data` directory, mounted to `/config`. The web terminal and file manager remain off. Browserless is a separate disposable-session tool and is not part of this app.

The app uses a vendored Docker v28.5.1 default seccomp profile with `unshare` additionally allowed. Source: `moby/moby` at `v28.5.1/vendor/github.com/moby/profiles/seccomp/default.json`; the vendored profile is under Moby's Apache-2.0 license (`nickseagull-chromium/SECCOMP-LICENSE`). **Security trade-off:** the original app ran with Chromium's `--no-sandbox` because its startup probe uses `clone(CLONE_NEWPID)`, which could not run with that seccomp change alone. This packaging revision adds `SYS_ADMIN` to the browser container so the upstream probe can attempt the renderer sandbox. `SYS_ADMIN` is a broad Docker capability that weakens the container boundary; it is not `privileged: true`. This is explicitly authorized by Nick, but **sandbox status remains unverified after the update**. Inspect `chrome://sandbox` before signing into accounts. The image's CDP implementation is documented upstream. An app manifest alone does not prove the updated app works on Nick's host.

### Installation and acceptance

1. If already installed, refresh the Community App Store and use Umbrel's **Update** action for **Chromium for RAMSYS** when offered. Otherwise install it from this store. Avoid uninstalling merely to apply the update: uninstall may erase `/config` browser data. Do not uninstall the existing Browserless app as part of this test.
2. Open its app tile and check that the graphical Chromium window loads. Inspect `chrome://version` for a profile path under `/config`; inspect `chrome://sandbox` for actual sandbox status.
3. From Hermes, check the app's CDP `/json/version` and connect via WebSocket. The browser displayed in the app tile and the CDP target must be the same instance.
4. Set a *synthetic expiring* cookie on a harmless test origin. Restart **only this browser app**, reconnect, read the cookie back, then delete it. A cookie visible only in the same session is insufficient evidence of persistence.
5. Only after those checks should Nick sign into web apps himself. Configure the active RAMSYS browser endpoint separately; do not transfer corthan credentials or resume cron jobs.

The manifest's icon points to this repository's `master` branch; it becomes available after the app change is merged. The app's package files live under `nickseagull-chromium/`.
