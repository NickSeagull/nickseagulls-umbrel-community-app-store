# Umbrel sources this file with its app environment loaded.
# Purpose-specific per-install database secret; never commit a live credential.
export APP_NICKSEAGULL_CODER_DB_PASSWORD="$(derive_entropy "${app_entropy_identifier}-postgres-password")"
# Umbrel's Docker socket group is host-specific; never hard-code a GID.
# If the socket is unavailable this expands empty and Compose fails closed.
export APP_NICKSEAGULL_CODER_DOCKER_GID="$(stat -c %g /var/run/docker.sock)"
