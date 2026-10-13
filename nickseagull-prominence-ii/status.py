"""Umbrel-authenticated, read-only setup/status page for the headless server."""
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
import socket

HOST = os.environ.get("MC_HOST", "server")
PORT = int(os.environ.get("MC_PORT", "25565"))
HTTP_PORT = int(os.environ.get("STATUS_PORT", "8080"))


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ("/", "/health"):
            self.send_error(404)
            return
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"ok\n")
            return
        try:
            with socket.create_connection((HOST, PORT), timeout=1):
                online = True
        except OSError:
            online = False
        label = "Listening on the private app network" if online else "Not listening yet"
        color = "#62d2a2" if online else "#ffba69"
        body = f"""<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Prominence II server</title>
<style>body{{background:#131722;color:#f4f4f5;font:17px system-ui;margin:4rem auto;max-width:44rem;padding:0 1.25rem;line-height:1.6}}
a{{color:#91c4ff}}code{{background:#272d3b;padding:.15rem .3rem;border-radius:.25rem}}
small{{color:#aeb6c7}}li{{margin:.75rem 0}}</style>
<h1>Prominence II: Hasturian Era</h1>
<p>Server: <strong style="color:{color}">{escape(label)}</strong></p>
<p>Fabric 1.20.1 · client pack v4.1.3 · Java 17 · private TCP 25565</p>
<ol><li>Accept the <a href="https://aka.ms/MinecraftEULA">Minecraft EULA</a>, then set
<code>EULA=TRUE</code> in this app's Umbrel Settings.</li>
<li>Create a <a href="https://playit.gg/account/setup/wizard/new-account/docker/docker-name">playit Docker agent</a>.
Set its generated key as <code>SECRET_KEY</code> in this app's Settings (do not share the key).
In playit's dashboard create a <b>Minecraft Java</b> tunnel targeting <code>127.0.0.1:25565</code>.
The agent shares the server's network namespace.</li>
<li>Add Minecraft usernames to <code>WHITELIST</code> in app Settings (comma separated),
then restart the app. Keep the whitelist enabled.</li>
<li>Give players playit's generated address and the matching
<a href="https://www.curseforge.com/minecraft/modpacks/prominence-2-hasturian-era/files/9094769">v4.1.3 client pack</a>.</li></ol>
<small>This page checks only the server TCP listener; it does not verify CurseForge installation,
Minecraft login, whitelist access or the public tunnel. Umbrel Settings store the playit key
as an ordinary environment value, not in a secret vault. Mod updates require a backup,
explicit CF_FILE_ID change and matching client update.</small></html>"""
        payload = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", HTTP_PORT), Handler).serve_forever()
