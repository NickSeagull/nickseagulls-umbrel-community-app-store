package tools

import (
	"context"
	"fmt"
	"github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/server"
	"github.com/nguyenvanduocit/telegram-mcp/services"
)

// Code and 2FA submission intentionally live only in the owner browser UI.
func RegisterAuthTools(s *server.MCPServer) {
	s.AddTool(mcp.NewTool("telegram_auth_status", mcp.WithDescription("Check current Telegram authentication status"), mcp.WithReadOnlyHintAnnotation(true)), mcp.NewTypedToolHandler(func(_ context.Context, _ mcp.CallToolRequest, _ struct{}) (*mcp.CallToolResult, error) {
		return mcp.NewToolResultText(fmt.Sprintf("Auth state: %s", services.GetAuthState())), nil
	}))
}
