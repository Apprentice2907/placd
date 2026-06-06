#!/bin/bash
set -e
echo "=== Placd Azure Setup ==="

sudo apt-get update -qq && sudo apt-get upgrade -y

# Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker azureuser
sudo systemctl enable docker
sudo systemctl start docker

# Dependencies
sudo apt-get install -y docker-compose-plugin git curl nano htop

# Open ports (Azure has TWO firewalls — NSG + iptables)
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 8000 -j ACCEPT
sudo apt-get install -y iptables-persistent
sudo netfilter-persistent save

sudo mkdir -p /opt/placd
sudo chown azureuser:azureuser /opt/placd

echo ""
echo "=== Setup complete ==="
echo "Next steps:"
echo "  git clone https://github.com/YOURUSERNAME/placd.git /opt/placd"
echo "  cd /opt/placd && cp .env.example .env && nano .env"
echo "  bash deploy/start.sh"
