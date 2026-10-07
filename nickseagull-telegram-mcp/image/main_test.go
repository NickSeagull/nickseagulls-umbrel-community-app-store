package main

import (
	"encoding/base64"
	"github.com/mark3labs/mcp-go/server"
	"github.com/nguyenvanduocit/telegram-mcp/tools"
	"net/http"
	"net/http/httptest"
	"net/url"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func request(h http.Handler, method, path, auth, body, csrf string) *httptest.ResponseRecorder {
	r := httptest.NewRequest(method, path, strings.NewReader(body))
	if auth != "" {
		r.Header.Set("Authorization", auth)
	}
	if body != "" {
		r.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	}
	if csrf != "" {
		r.Header.Set("X-CSRF-Token", csrf)
	}
	w := httptest.NewRecorder()
	h.ServeHTTP(w, r)
	return w
}
func basic(s string) string { return "Basic " + base64.StdEncoding.EncodeToString([]byte("owner:"+s)) }
func TestUnconfiguredIsHealthyButPrivate(t *testing.T) {
	a, err := newApp(t.TempDir(), "test-owner-password", "test-mcp-token", false)
	if err != nil {
		t.Fatal(err)
	}
	h := a.routes()
	for _, path := range []string{"/", "/mcp", "/setup", "/auth/code"} {
		if w := request(h, "GET", path, "", "", ""); w.Code != http.StatusUnauthorized {
			t.Errorf("%s: %d", path, w.Code)
		}
	}
	if w := request(h, "POST", "/mcp", "", "", ""); w.Code != http.StatusUnauthorized {
		t.Errorf("mcp: %d", w.Code)
	}
	if w := request(h, "GET", "/healthz", "", "", ""); w.Code != 200 || !strings.Contains(w.Body.String(), `"state":"unconfigured"`) {
		t.Errorf("health: %d %s", w.Code, w.Body.String())
	}
	if w := request(h, "GET", "/mcp", basic("test-owner-password"), "", ""); w.Code != http.StatusUnauthorized {
		t.Errorf("owner password must not authorize MCP: %d", w.Code)
	}
	if w := request(h, "GET", "/mcp", "Bearer test-mcp-token", "", ""); w.Code != http.StatusServiceUnavailable {
		t.Errorf("unconfigured mcp: %d", w.Code)
	}
	if w := request(h, "GET", "/", "Bearer test-mcp-token", "", ""); w.Code != http.StatusUnauthorized {
		t.Errorf("MCP token must not authorize owner UI: %d", w.Code)
	}
}
func TestSetupNeedsCSRFAndPersistsPrivately(t *testing.T) {
	dir := t.TempDir()
	a, err := newApp(dir, "test-owner-password", "test-mcp-token", false)
	if err != nil {
		t.Fatal(err)
	}
	h := a.routes()
	form := url.Values{"api_id": {"12345"}, "api_hash": {"abc123"}, "phone": {"+10000000000"}}.Encode()
	if w := request(h, "POST", "/setup", basic("test-owner-password"), form, ""); w.Code != http.StatusForbidden {
		t.Fatalf("no csrf: %d", w.Code)
	}
	if w := request(h, "POST", "/setup", basic("wrong"), form, a.csrf); w.Code != http.StatusUnauthorized {
		t.Fatalf("wrong password: %d", w.Code)
	}
	if _, err := os.Stat(filepath.Join(dir, "credentials.json")); !os.IsNotExist(err) {
		t.Fatalf("created without authorization: %v", err)
	}
	w := request(h, "POST", "/setup", basic("test-owner-password"), form, a.csrf)
	if w.Code != http.StatusSeeOther {
		t.Fatalf("setup: %d %s", w.Code, w.Body.String())
	}
	b, err := os.ReadFile(filepath.Join(dir, "credentials.json"))
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(string(b), "abc123") {
		t.Fatal("credentials missing")
	}
	st, err := os.Stat(filepath.Join(dir, "credentials.json"))
	if err != nil || st.Mode().Perm() != 0600 {
		t.Fatalf("credential permissions: %v %v", st, err)
	}
	if w := request(h, "GET", "/", basic("test-owner-password"), "", ""); strings.Contains(w.Body.String(), "abc123") || strings.Contains(w.Body.String(), "+10000000000") {
		t.Fatal("secret leaked in UI")
	}
	if w := request(h, "POST", "/setup", basic("test-owner-password"), form, a.csrf); w.Code != http.StatusConflict {
		t.Errorf("overwrite: %d", w.Code)
	}
	again, err := newApp(dir, "test-owner-password", "test-mcp-token", false)
	if err != nil || again.state() == "unconfigured" {
		t.Fatalf("credentials not persisted across restart: %v", err)
	}
}
func TestAuthToolsCannotCarryCodesThroughMCP(t *testing.T) {
	s := server.NewMCPServer("test", "1")
	tools.RegisterAuthTools(s)
	entries := s.ListTools()
	if _, ok := entries["telegram_auth_status"]; !ok {
		t.Fatal("missing auth status")
	}
	for _, name := range []string{"telegram_auth_send_code", "telegram_auth_send_password"} {
		if _, ok := entries[name]; ok {
			t.Errorf("sensitive MCP tool exposed: %s", name)
		}
	}
}

func TestNoSecretInHealthAndAuthSubmissionGuarded(t *testing.T) {
	a, err := newApp(t.TempDir(), "test-owner-password", "test-mcp-token", false)
	if err != nil {
		t.Fatal(err)
	}
	h := a.routes()
	for _, path := range []string{"/auth/code", "/auth/password"} {
		form := url.Values{"value": {"private-code-or-password"}}.Encode()
		if w := request(h, "POST", path, "", form, a.csrf); w.Code != 401 {
			t.Errorf("unauthorized %s: %d", path, w.Code)
		}
		if w := request(h, "POST", path, basic("test-owner-password"), form, ""); w.Code != 403 {
			t.Errorf("csrf %s: %d", path, w.Code)
		}
	}
	if w := request(h, "GET", "/healthz", "", "", ""); strings.Contains(w.Body.String(), "test-owner-password") {
		t.Fatal("secret in health")
	}
}
