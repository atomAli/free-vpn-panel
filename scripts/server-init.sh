#!/usr/bin/env bash
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "This script must run as root. Try: sudo bash server-init.sh"
  exit 1
fi

echo "==> [1/6] Updating system"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get upgrade -y
apt-get install -y curl jq openssl netfilter-persistent

echo "==> [2/6] Opening port 443 in Oracle default iptables"
iptables -C INPUT -p tcp --dport 443 -j ACCEPT 2>/dev/null || iptables -I INPUT -p tcp --dport 443 -j ACCEPT
netfilter-persistent save

echo "==> [3/6] Enabling BBR congestion control"
cat >/etc/sysctl.d/99-proxy-tuning.conf <<'EOF'
net.core.default_qdisc=fq
net.ipv4.tcp_congestion_control=bbr
net.ipv4.tcp_fastopen=3
net.ipv4.tcp_slow_start_after_idle=0
EOF
sysctl --system >/dev/null
sysctl net.ipv4.tcp_congestion_control

echo "==> [4/6] Raising file descriptor limits"
cat >/etc/security/limits.d/99-proxy.conf <<'EOF'
* soft nofile 65535
* hard nofile 65535
EOF

TOTAL_MB=$(awk '/MemTotal/{print int($2/1024)}' /proc/meminfo)
if [ "$TOTAL_MB" -le 2500 ] && ! swapon --show | grep -q swapfile; then
  echo "==> Small instance detected, creating 2G swap"
  fallocate -l 2G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  grep -q '/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >>/etc/fstab
fi

echo "==> [5/6] Installing Marzban (official installer)"
bash -c "$(curl -sL https://github.com/Gozargah/Marzban-scripts/raw/master/marzban.sh)" @ install

echo "==> Waiting for Marzban to start..."
sleep 10
docker ps --format '{{.Names}}\t{{.Status}}' | grep -i marzban || true

echo ""
echo "==> [6/6] Generating Reality keys (save these!)"
KEYS=$(docker exec marzban_marzban_1 xray x25519)
PRIVATE_KEY=$(echo "$KEYS" | awk '/Private key/{print $3}')
PUBLIC_KEY=$(echo "$KEYS" | awk '/Public key/{print $3}')
SHORT_ID=$(openssl rand -hex 8)
UUID=$(cat /proc/sys/kernel/random/uuid)

echo ""
echo "======================================================="
echo " PRIVATE_KEY : $PRIVATE_KEY"
echo " PUBLIC_KEY  : $PUBLIC_KEY   (client 'pbk' value)"
echo " SHORT_ID    : $SHORT_ID     (client 'sid' value)"
echo " UUID sample : $UUID         (Marzban makes its own)"
echo "======================================================="
echo ""
echo "Next steps:"
echo " 1) Create admin:            marzban-cli admin create --sudo"
echo " 2) Open panel via tunnel on YOUR machine:"
echo "    ssh -N -L 8000:127.0.0.1:8000 ubuntu@SERVER_IP"
echo "    then browse: http://localhost:8000/dashboard"
echo " 3) Paste configs/xray-core-settings.json into Core Settings,"
echo "    replacing __PRIVATE_KEY__ and __SHORT_ID__ with values above."
echo " 4) Restart core from the dashboard."
