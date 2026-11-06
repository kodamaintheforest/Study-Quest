# Study Quest: From Zero to Root

**Level up a character by leveling up yourself.** Study Quest is a gamified cybersecurity learning tracker. Every skill you practice, cert you earn, and hour you study turns into XP for your character.

> **Beta:** Study Quest is still in early development. A lot of features are unfinished, some characters and homes don't have art yet, and things may break. Feedback is welcome.

## Features

**Character and XP**
- Log what you learned as Easy, Medium, or Hard (10, 25, or 50 XP), with optional bonus XP
- Red team stats: Recon, Exploitation, Privilege Escalation, C2 / Persistence, Evasion
- Blue team stats: Log Analysis, Detection Engineering, Incident Response, Threat Hunting, Hardening
- Leveling gets harder as you go, with tier evolutions at level 36 and level 65

**Certifications**
- Track certs as Planned, In Progress, or Earned
- Earned certs award XP (Security+, CySA+, CEH, OSCP, CISSP, SC-200, and more)

**Study Mode**
- Session timer with pause and resume
- Checkpoint notes during a session and a nudge reminder to keep you on track
- Session history you can edit or delete, with XP awarded when you finish

**Character Roster**
- 11 characters across 3 classes: Attackers (red), Defenders (blue), and Watchers (purple)
- Characters and their tiers unlock as you level up

**Homes**
- Start in Mom's Basement and work your way up to The Invisible Home at level 100
- Side-view scene renderer for each home

**Notebook**
- Folder-style notes with a split-view markdown editor and live preview
- Code highlighting, wiki-style links between notes, image uploads, full-text search, and autosave

**Tool Tracker**
- Check off red team tools by kill chain phase (Nmap, Burp Suite, Metasploit, BloodHound, and more)
- Check off blue team tools by category (Splunk, Wireshark, Sysmon, Volatility, and more)

**Knowledge Log, Diary, and To-Do List**
- Every XP award gets logged automatically, so you have a record of what you learned
- A personal diary with editable entries
- A to-do list split into sections like projects, school work, and chores

## Run it

```
pip install -r requirements.txt
python app.py
```

Then open http://127.0.0.1:5000 in your browser.

Everything runs locally on your machine. Your progress is saved in a `data/` folder that gets created the first time you run it.

## Built with
Python, Flask, vanilla JavaScript, HTML and CSS

## Roadmap
- Art for the remaining characters and homes
- Interactive homes with walking characters
- A lifetime study hours counter
- More classes, effects, and features

## Dedication
Cyber Viking is dedicated to my brother Donald Caswell, who created his character for this project.

## About
Built by Kevin Ceniceros while making the move from construction into cybersecurity.
[LinkedIn](https://linkedin.com/in/kevin-ceniceros-it)
