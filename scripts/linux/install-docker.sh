#!/usr/bin/env bash
# Installs Docker Engine + Compose plugin from Docker's official apt repository (docs.docker.com/engine/install/ubuntu).
# Run as root inside the Alice WSL distro. Idempotent.
set -euo pipefail

USER_NAME="${1:-alice}"

if ! command -v docker >/dev/null 2>&1; then
  apt-get update -q
  apt-get install -y -q ca-certificates curl
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  . /etc/os-release
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${UBUNTU_CODENAME:-$VERSION_CODENAME} stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -q
  apt-get install -y -q docker-ce docker-ce-cli containerd.io docker-compose-plugin
fi

# Daemon: local unix socket only (no TCP), log rotation so container logs can't fill the VHD.
mkdir -p /etc/docker
cat > /etc/docker/daemon.json <<'JSON'
{
  "hosts": ["unix:///var/run/docker.sock"],
  "log-driver": "json-file",
  "log-opts": { "max-size": "10m", "max-file": "3" },
  "live-restore": true
}
JSON

# Membership in 'docker' is root-equivalent; only this user (the one Alice's broker runs as) gets it.
id "$USER_NAME" >/dev/null 2>&1 || useradd -m -s /bin/bash "$USER_NAME"
usermod -aG docker "$USER_NAME"

systemctl enable docker.service containerd.service >/dev/null 2>&1 || true
systemctl restart docker || true
docker version --format 'docker server {{.Server.Version}}'
docker compose version
