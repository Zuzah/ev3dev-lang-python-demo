# EV3Dev Project — Claude Code Context

## Who I Am
Senior Software Engineer, comfortable with Python, Linux, CLI, macOS.
I'm working on LEGO Mindstorms EV3 robotics projects using ev3dev,
often with a 7-year-old child learning alongside me.

## Hardware & Environment
- LEGO Mindstorms EV3 brick (received 2025)
- ev3dev-stretch-ev3-generic-2020-04-10 flashed via `dd` on macOS
- microSD 4–32GB (no larger)
- macOS as dev machine
- EV3 connected via USB with internet sharing enabled (System Settings → Sharing)
- SSH: `ssh robot@ev3dev.local` (password: maker)
- Internet sharing: WiFi → EV3dev interface, enabled AFTER selecting source

## My Workflow
1. Write/edit code on Mac in VSCode or terminal
2. Create destination dir on EV3 first (SCP fails silently if it doesn't exist): `ssh robot@ev3dev.local "mkdir -p /home/robot/PROJECT"`
3. Copy to EV3: `scp -r /path/to/project robot@ev3dev.local:/home/robot/`
4. Make executable: `ssh robot@ev3dev.local "chmod +x /home/robot/PROJECT/script.py"`
5. Fix shebang if needed: `#!/usr/bin/env micropython` → `#!/usr/bin/env python3`
6. Run and capture output (stdout + stderr): `ssh robot@ev3dev.local "python3 /home/robot/PROJECT/script.py" 2>&1`

## Debugging on EV3
- Always run scripts via SSH (`python3 script.py 2>&1`) to see Python tracebacks — the EV3 menu swallows output
- `journalctl` only shows system/boot events, not Python script output — don't use it to debug scripts
- If the EV3 menu says "not executable": `chmod +x` the file and verify the shebang is `#!/usr/bin/env python3`

## Primary Repos
- Main: https://github.com/ev3dev/ev3dev-lang-python-demo
- Secondary (R3PTAR): https://github.com/Chrisontour/r3ptar03

## Known Issues / Lessons Learned
- Etcher (new versions) breaks ev3dev images — always use `dd`
- `dd` target must be `/dev/rdisk6` (raw), not `/dev/disk6` (buffered) on macOS
- Must `diskutil unmountDisk` before flashing
- Must unzip `.img` from `.zip` before flashing — dd cannot flash `.zip`
- Some demo scripts use `micropython` shebang — change to `python3` for ev3dev
- microSD must be 4–32GB max — larger cards may not work

## Active Project
- R3PTAR snake robot build
- Using ev3dev2 Python library
- Exploring ev3dev-lang-python-demo as reference

## What I Need From You (Claude Code)
- Help me write, debug, and deploy Python code for ev3dev
- Understand motor ports (A/B/C/D), sensor ports (1/2/3/4)
- Use ev3dev2 library as default (`from ev3dev2.motor import *`)
- Warn me about hardware risks (stall, overcurrent, wrong port)
- Keep code clean, well-commented, readable by a child with guidance
- When suggesting deploy steps, use my exact workflow above
- Flag when something requires physical EV3 access vs can be tested in code