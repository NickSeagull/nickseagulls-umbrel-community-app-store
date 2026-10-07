// Telegram MCP Umbrel wrapper: one private HTTP listener, never the upstream public listener.
package main

import (
	"context"
	"crypto/rand"
	"crypto/subtle"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"html/template"

	"log"
	"net/http"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/mark3labs/mcp-go/server"
	"github.com/nguyenvanduocit/telegram-mcp/services"
	"github.com/nguyenvanduocit/telegram-mcp/tools"
)

type credentials struct {
	APIID   int    `json:"api_id"`
	APIHash string `json:"api_hash"`
	Phone   string `json:"phone"`
}
type app struct {
	dir, owner, mcpToken, csrf string
	launch                     bool
	mu                         sync.Mutex
	configured, failed         bool
	mcp                        http.Handler
}

func newApp(dir, owner, mcpToken string, launch bool) (*app, error) {
	if owner == "" {
		return nil, errors.New("TELEGRAM_MCP_OWNER_PASSWORD is required")
	}
	if mcpToken == "" || mcpToken == owner {
		return nil, errors.New("TELEGRAM_MCP_TOKEN must be set and distinct from owner password")
	}
	if dir == "" {
		return nil, errors.New("TELEGRAM_MCP_DATA_DIR is required")
	}
	if err := os.MkdirAll(dir, 0700); err != nil {
		return nil, err
	}
	if err := os.Chmod(dir, 0700); err != nil {
		return nil, err
	}
	nonce := make([]byte, 32)
	if _, err := rand.Read(nonce); err != nil {
		return nil, err
	}
	a := &app{dir: dir, owner: owner, mcpToken: mcpToken, csrf: hex.EncodeToString(nonce), launch: launch}
	c, err := a.readCredentials()
	if err == nil {
		a.configured = true
		if launch {
			a.start(c)
		}
	} else if !errors.Is(err, os.ErrNotExist) {
		return nil, fmt.Errorf("read credentials: %w", err)
	}
	m := server.NewMCPServer("Telegram MCP", "1.0.0", server.WithRecovery())
	// Authentication codes and 2FA are deliberately accepted only by the owner's browser form.
	// All operational upstream tools and prompts remain registered unchanged.
	tools.RegisterAuthTools(m)
	tools.RegisterMessageTools(m)
	tools.RegisterChatTools(m)
	tools.RegisterMediaTools(m)
	tools.RegisterUserTools(m)
	tools.RegisterReactionTools(m)
	tools.RegisterInviteTools(m)
	tools.RegisterNotificationTools(m)
	tools.RegisterContactTools(m)
	tools.RegisterForumTools(m)
	tools.RegisterStoryTools(m)
	tools.RegisterAdminTools(m)
	tools.RegisterFolderTools(m)
	tools.RegisterProfileTools(m)
	tools.RegisterDraftTools(m)
	tools.RegisterCompoundTools(m)
	tools.RegisterPrompts(m)
	a.mcp = server.NewStreamableHTTPServer(m, server.WithEndpointPath("/mcp"))
	return a, nil
}
func (a *app) readCredentials() (credentials, error) {
	var c credentials
	b, err := os.ReadFile(filepath.Join(a.dir, "credentials.json"))
	if err != nil {
		return c, err
	}
	if err = json.Unmarshal(b, &c); err != nil {
		return c, err
	}
	if c.APIID <= 0 || c.APIHash == "" || c.Phone == "" {
		return c, errors.New("incomplete credentials")
	}
	return c, nil
}
func (a *app) start(c credentials) {
	os.Setenv("TELEGRAM_API_ID", strconv.Itoa(c.APIID))
	os.Setenv("TELEGRAM_API_HASH", c.APIHash)
	os.Setenv("TELEGRAM_PHONE", c.Phone)
	os.Setenv("TELEGRAM_SESSION_DIR", filepath.Join(a.dir, "session"))
	go func() {
		if err := services.StartTelegram(context.Background()); err != nil {
			log.Printf("Telegram startup failed (details withheld from logs)")
			a.mu.Lock()
			a.failed = true
			a.mu.Unlock()
		}
	}()
}
func (a *app) state() string {
	a.mu.Lock()
	configured, failed := a.configured, a.failed
	a.mu.Unlock()
	if !configured {
		return "unconfigured"
	}
	if failed {
		return "error"
	}
	return string(services.GetAuthState())
}
func (a *app) authorized(r *http.Request) bool {
	u, p, ok := r.BasicAuth()
	return ok && u == "owner" && subtle.ConstantTimeCompare([]byte(p), []byte(a.owner)) == 1
}
func (a *app) authorizedMCP(r *http.Request) bool {
	h := r.Header.Get("Authorization")
	if !strings.HasPrefix(h, "Bearer ") {
		return false
	}
	return subtle.ConstantTimeCompare([]byte(strings.TrimPrefix(h, "Bearer ")), []byte(a.mcpToken)) == 1
}
func (a *app) protect(next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if !a.authorized(r) {
			w.Header().Set("WWW-Authenticate", `Basic realm="Telegram MCP owner"`)
			http.Error(w, "authentication required", 401)
			return
		}
		next(w, r)
	}
}
func (a *app) checkForm(w http.ResponseWriter, r *http.Request) bool {
	if r.Method != "POST" {
		http.Error(w, "method not allowed", 405)
		return false
	}
	if r.Header.Get("Content-Type") != "application/x-www-form-urlencoded" {
		http.Error(w, "form required", 415)
		return false
	}
	if origin := r.Header.Get("Origin"); origin != "" && origin != "http://"+r.Host && origin != "https://"+r.Host {
		http.Error(w, "origin rejected", 403)
		return false
	}
	r.Body = http.MaxBytesReader(w, r.Body, 4096)
	if err := r.ParseForm(); err != nil {
		http.Error(w, "invalid form", 400)
		return false
	}
	token := r.Form.Get("csrf")
	if token == "" {
		token = r.Header.Get("X-CSRF-Token")
	}
	if subtle.ConstantTimeCompare([]byte(token), []byte(a.csrf)) != 1 {
		http.Error(w, "CSRF rejected", 403)
		return false
	}
	return true
}

var page = template.Must(template.New("ui").Parse(`<!doctype html><html><head><meta charset="utf-8"><title>Telegram MCP setup</title></head><body><h1>Telegram MCP</h1><p>Status: {{.State}}</p>{{if eq .State "unconfigured"}}<p>Get your API ID and hash at <a href="https://my.telegram.org/apps">my.telegram.org/apps</a>.</p><form method="post" action="/setup"><input type="hidden" name="csrf" value="{{.CSRF}}"><label>API ID <input name="api_id" required inputmode="numeric"></label><label>API hash <input name="api_hash" required></label><label>Phone <input name="phone" required></label><button>Save and connect</button></form>{{else if eq .State "waiting_code"}}<form method="post" action="/auth/code"><input type="hidden" name="csrf" value="{{.CSRF}}"><label>Telegram verification code <input name="value" required autocomplete="one-time-code"></label><button>Submit code</button></form>{{else if eq .State "waiting_password"}}<form method="post" action="/auth/password"><input type="hidden" name="csrf" value="{{.CSRF}}"><label>Telegram 2FA password <input name="value" type="password" required autocomplete="off"></label><button>Submit password</button></form>{{else if eq .State "authenticated"}}<p>MCP endpoint: /mcp (separate Bearer token required).</p>{{else}}<p>Connecting or unavailable. Refresh for status; inspect private service logs if it persists.</p>{{end}}</body></html>`))

func (a *app) routes() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("/healthz", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "GET" {
			http.Error(w, "method not allowed", 405)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(map[string]string{"state": a.state()})
	})
	mux.HandleFunc("/", a.protect(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/" || r.Method != "GET" {
			http.NotFound(w, r)
			return
		}
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		_ = page.Execute(w, map[string]string{"State": a.state(), "CSRF": a.csrf})
	}))
	mux.HandleFunc("/setup", a.protect(func(w http.ResponseWriter, r *http.Request) {
		if !a.checkForm(w, r) {
			return
		}
		id, err := strconv.Atoi(r.Form.Get("api_id"))
		hash, phone := strings.TrimSpace(r.Form.Get("api_hash")), strings.TrimSpace(r.Form.Get("phone"))
		if err != nil || id <= 0 || hash == "" || phone == "" {
			http.Error(w, "invalid credentials", 400)
			return
		}
		c := credentials{APIID: id, APIHash: hash, Phone: phone}
		b, _ := json.Marshal(c)
		a.mu.Lock()
		defer a.mu.Unlock()
		if a.configured {
			http.Error(w, "already configured; stop service and remove credentials to reset", 409)
			return
		}
		f, err := os.OpenFile(filepath.Join(a.dir, "credentials.json"), os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0600)
		if err != nil {
			http.Error(w, "could not save credentials", 500)
			return
		}
		_, err = f.Write(b)
		closeErr := f.Close()
		if err != nil || closeErr != nil {
			http.Error(w, "could not save credentials", 500)
			return
		}
		a.configured = true
		if a.launch {
			a.start(c)
		}
		http.Redirect(w, r, "/", http.StatusSeeOther)
	}))
	for _, item := range []struct {
		path   string
		state  services.AuthState
		submit func(string) (services.AuthState, error)
	}{{"/auth/code", services.AuthStateWaitingCode, services.SubmitCode}, {"/auth/password", services.AuthStateWaitingPassword, services.SubmitPassword}} {
		item := item
		mux.HandleFunc(item.path, a.protect(func(w http.ResponseWriter, r *http.Request) {
			if !a.checkForm(w, r) {
				return
			}
			if services.GetAuthState() != item.state || a.state() == "unconfigured" {
				http.Error(w, "not waiting for this input", 409)
				return
			}
			value := r.Form.Get("value")
			if value == "" || len(value) > 1024 {
				http.Error(w, "invalid input", 400)
				return
			}
			if _, err := item.submit(value); err != nil {
				http.Error(w, "Telegram rejected input or timed out", 409)
				return
			}
			http.Redirect(w, r, "/", http.StatusSeeOther)
		}))
	}
	mux.HandleFunc("/mcp", func(w http.ResponseWriter, r *http.Request) {
		if !a.authorizedMCP(r) {
			http.Error(w, "authentication required", 401)
			return
		}
		if origin := r.Header.Get("Origin"); origin != "" && origin != "http://"+r.Host && origin != "https://"+r.Host {
			http.Error(w, "origin rejected", 403)
			return
		}
		if a.state() != "authenticated" {
			http.Error(w, "Telegram not authenticated", 503)
			return
		}
		a.mcp.ServeHTTP(w, r)
	})
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Cache-Control", "no-store")
		w.Header().Set("X-Content-Type-Options", "nosniff")
		w.Header().Set("Content-Security-Policy", "default-src 'none'; form-action 'self'; style-src 'unsafe-inline'; frame-ancestors 'none'")
		mux.ServeHTTP(w, r)
	})
}
func main() {
	dir := os.Getenv("TELEGRAM_MCP_DATA_DIR")
	if dir == "" {
		dir = "/data"
	}
	a, err := newApp(dir, os.Getenv("TELEGRAM_MCP_OWNER_PASSWORD"), os.Getenv("TELEGRAM_MCP_TOKEN"), true)
	if err != nil {
		log.Fatal(err)
	}
	addr := os.Getenv("TELEGRAM_MCP_LISTEN")
	if addr == "" {
		addr = ":8080"
	}
	srv := &http.Server{Addr: addr, Handler: a.routes(), ReadHeaderTimeout: 5 * time.Second, MaxHeaderBytes: 8192}
	log.Printf("Telegram MCP wrapper listening on %s", addr)
	if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		log.Fatal(err)
	}
}
