#!/bin/bash
# Run once after deployment
(crontab -l 2>/dev/null; cat << 'EOF'
# Placd keepalive — every 5 minutes
*/5 * * * * /opt/placd/deploy/keepalive.sh >> /var/log/placd.log 2>&1
# Log rotation — weekly
0 0 * * 0 truncate -s 0 /var/log/placd.log
EOF
) | crontab -
echo "Cron jobs installed"
