#!/usr/bin/env python
from pathlib import Path
import sys

cwd = Path(__file__).parent 
user_home = Path(sys.executable.split('/.pyenv')[0])

service_path = Path("/etc/systemd/system/balance_the_force@.service")
contents = f'''[Unit]
Description=Discord Bot for balancing teams
After=multi-user.target
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=%i
WorkingDirectory={cwd}
ExecStart={user_home}/.pyenv/shims/python balance_the_force.py
'''

with open(service_path,"w") as file:
    file.write(contents)
    file.close()
