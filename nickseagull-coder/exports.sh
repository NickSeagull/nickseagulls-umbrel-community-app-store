# Umbrel sources this file with its app environment loaded.
# Purpose-specific per-install database secret; never commit a live credential.
export APP_NICKSEAGULL_CODER_DB_PASSWORD="$(derive_entropy "${app_entropy_identifier}-postgres-password")"
