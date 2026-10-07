export APP_NICKSEAGULL_MCTL_TELEGRAM_JWT_KEY="$(derive_entropy "${app_entropy_identifier}-oauth-jwt-key")"
export APP_NICKSEAGULL_MCTL_TELEGRAM_ENCRYPTION_KEY="$(derive_entropy "${app_entropy_identifier}-session-encryption-key")"
export APP_NICKSEAGULL_MCTL_TELEGRAM_DB_KEY="$(derive_entropy "${app_entropy_identifier}-postgres-password")"
