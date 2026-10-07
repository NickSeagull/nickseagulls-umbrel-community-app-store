package tools

import (
	"context"
	"os"
	"path/filepath"
	"testing"

	"github.com/mark3labs/mcp-go/mcp"
)

func TestSendStoryRejectsSecretPathBeforeTelegram(t *testing.T) {
	root := t.TempDir()
	t.Setenv("TELEGRAM_MCP_MEDIA_DIR", root)
	secret := filepath.Join(t.TempDir(), "credentials.json")
	if err := os.WriteFile(secret, []byte("secret"), 0600); err != nil {
		t.Fatal(err)
	}
	result, err := handleSendStory(context.Background(), mcp.CallToolRequest{}, sendStoryInput{Peer: "123", FilePath: secret})
	if err != nil {
		t.Fatal(err)
	}
	if result == nil || !result.IsError {
		t.Fatal("out-of-media upload was not rejected")
	}
}
