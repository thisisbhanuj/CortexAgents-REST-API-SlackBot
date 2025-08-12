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

# Reload systemd and enable service
systemctl daemon-reload
systemctl enable slackbot.service
systemctl start slackbot.service
