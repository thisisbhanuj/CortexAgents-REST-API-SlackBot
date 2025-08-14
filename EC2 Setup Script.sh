#!/bin/bash
set -e

# Update & install essentials
yum update -y
yum install -y python3 git

# Upgrade pip
python3 -m ensurepip --upgrade
python3 -m pip install --upgrade pip

# Switch to ec2-user home
cd /home/ec2-user

# Clone your Slack bot repo
git clone https://github.com/thisisbhanuj/CortexAgents-REST-API-SlackBot.git app

cd app

# Create venv and install deps
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create .env file - EDIT tokens here or replace with Secrets Manager logic
cat > .env <<EOF
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-token
EOF

chown ec2-user:ec2-user .env

# Create systemd service file
cat > /etc/systemd/system/slackbot.service <<EOF
[Unit]
Description=Slack Bolt App
After=network.target

[Service]
User=ec2-user
WorkingDirectory=/home/ec2-user/app
EnvironmentFile=/home/ec2-user/app/.env
ExecStart=/home/ec2-user/app/venv/bin/python /home/ec2-user/app/app.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Commands #######################################
# Stop the service immediately
sudo systemctl stop slackbot.service
# Disable it from starting at boot
sudo systemctl disable slackbot.service
# Reload systemd manager configuration
sudo systemctl daemon-reload
# (Optional) Restart the service to apply changes
sudo systemctl restart slackbot.service
# Check the status of the service
systemctl status slackbot.service
# Verify if the service is enabled to start at boot
systemctl is-enabled slackbot.service
