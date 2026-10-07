package tools

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/mark3labs/mcp-go/server"
)

func TestMediaDownloadIsAnnotatedAsWrite(t *testing.T) {
	s := server.NewMCPServer("media-test", "1")
	RegisterMediaTools(s)
	tool, ok := s.ListTools()["telegram_download_media"]
	if !ok || tool.Tool.Annotations.ReadOnlyHint == nil || *tool.Tool.Annotations.ReadOnlyHint {
		t.Fatal("media download is a filesystem write and must not be marked read-only")
	}
}

func TestMediaUploadConfinedToMediaRoot(t *testing.T) {
	root := t.TempDir()
	t.Setenv("TELEGRAM_MCP_MEDIA_DIR", root)
	allowed := filepath.Join(root, "photo.jpg")
	if err := os.WriteFile(allowed, []byte("photo"), 0600); err != nil {
		t.Fatal(err)
	}
	secret := filepath.Join(t.TempDir(), "credentials.json")
	if err := os.WriteFile(secret, []byte("secret"), 0600); err != nil {
		t.Fatal(err)
	}
	f, err := openMediaUpload(allowed)
	if err != nil {
		t.Fatalf("allowed upload: %v", err)
	}
	f.Close()
	for _, path := range []string{secret, filepath.Join(root, "..", filepath.Base(filepath.Dir(secret)), "credentials.json"), filepath.Join(root, "escape"), filepath.Join(root, "nested", "photo.jpg")} {
		if path == filepath.Join(root, "escape") {
			if err := os.Symlink(secret, path); err != nil {
				t.Fatal(err)
			}
		}
		if f, err := openMediaUpload(path); err == nil {
			f.Close()
			t.Errorf("allowed protected upload: %s", path)
		}
	}
}

func TestMediaDownloadConfinedAndExclusive(t *testing.T) {
	root := t.TempDir()
	t.Setenv("TELEGRAM_MCP_MEDIA_DIR", root)
	for _, name := range []string{"../credentials.json", "/data/session.json", "nested/file", ""} {
		if f, _, err := createMediaDownload(name); err == nil {
			f.Close()
			t.Errorf("allowed invalid download name: %q", name)
		}
	}
	file, path, err := createMediaDownload("photo-1.jpg")
	if err != nil {
		t.Fatal(err)
	}
	file.Close()
	if path != filepath.Join(root, "photo-1.jpg") {
		t.Errorf("unexpected destination %q", path)
	}
	if file, _, err := createMediaDownload("photo-1.jpg"); err == nil {
		file.Close()
		t.Fatal("overwrote existing file")
	}
	outside := filepath.Join(t.TempDir(), "secret")
	if err := os.WriteFile(outside, []byte("secret"), 0600); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(outside, filepath.Join(root, "link")); err != nil {
		t.Fatal(err)
	}
	if file, _, err := createMediaDownload("link"); err == nil {
		file.Close()
		t.Fatal("followed symlink")
	}
}
