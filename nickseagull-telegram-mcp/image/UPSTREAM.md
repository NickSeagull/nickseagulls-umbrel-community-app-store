# Source and modifications

- Upstream: https://github.com/nguyenvanduocit/telegram-mcp at commit `b57f47d93ed1d3e05fe615db5640a05740aea043`.
- The upstream README states MIT. That commit does not contain a standalone LICENSE file; confirm license metadata before redistributing beyond this community-store deployment.
- `services/telegram.go` and `tools/` are copies from that commit; `tools/telegram_auth.go` registers status only. `main.go` and `main_test.go` implement Umbrel setup and authenticated HTTP around upstream code.
- Do not print or commit Telegram API credentials, login codes, 2FA passwords, session files or generated Umbrel secrets.
