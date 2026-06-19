# 🤖 AutoDebug

> A 5-agent autonomous bug detection and reporting pipeline, built natively on Band.

[![License](https://img.shields.io/badge/License-Apache%202.0-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![Band](https://img.shields.io/badge/Built%20with-Band-orange.svg)](https://band.ai)
[![Hackathon](https://img.shields.io/badge/Band%20of%20Agents-Hackathon%202026-purple.svg)](https://lablab.ai)

---

## What is AutoDebug?

AutoDebug is a 5-agent system that detects bugs in a GitHub repository, analyses the root cause, generates a fix, confirms the bug through testing, and delivers a clear, actionable fix report by email — with zero auto-merging. A human always reviews and applies the fix.

The 5 agents are real, independent processes connected to Band. They coordinate entirely through Band chat rooms using @mentions — Band is not a wrapper here, it's the actual communication layer the agents depend on to hand off work.

---

## Architecture
@AutoDebug-Detector detect <repo> <commit> <branch>

↓ (Band room, @mention)

DetectorAgent

clones repo
finds failed CI run, or runs files directly to catch the error

↓ @AutoDebug-Analyser (Band)

AnalyserAgent
AI root cause analysis, severity rating

↓ @AutoDebug-Fixer (Band)

FixerAgent
generates a suggested code fix

↓ @AutoDebug-Tester (Band)

TesterAgent
runs pytest, confirms the bug is real

↓ @AutoDebug-Resolver (Band)

ResolverAgent
writes a human-readable fix report
triggers email + DevOps AI Notifier


Each agent is a standalone Python process built with Band's `SimpleAdapter`. They run continuously (`agent.run_forever()`), listening in a shared Band chat room, and hand off work to the next agent by sending an @mention with the accumulated context as JSON.

---

## The 5 Agents

| Agent | Role | Hands off to |
|---|---|---|
| **Detector** | Finds the bug — from CI logs or by running files directly | Analyser |
| **Analyser** | AI-powered root cause analysis and severity rating | Fixer |
| **Fixer** | Generates a suggested code fix | Tester |
| **Tester** | Runs pytest, confirms the bug is real | Resolver |
| **Resolver** | Writes the fix report, sends email, triggers DevOps Notifier | — |

---

## Key Features

- **Real Band-native agents** — 5 separate registered agents, coordinating through @mentions in a shared room
- **Human-in-the-loop by design** — never auto-merges. Every fix is a report, not a commit
- **Email delivery** — final fix report lands directly in your inbox
- **DevOps AI Notifier integration** — connects to a second existing project for summarised notifications
- **CLI management** — `autodebug start/stop/status/doctor` manages all 5 agents without 5 manual terminals
- **Local fallback pipeline** — `agents/` + `core/pipeline.py` provide the same 5-stage logic outside Band, useful for offline testing

---

## Tech Stack

- **Band SDK** (`band-sdk`) — agent registration, rooms, @mention routing
- **NVIDIA API** (MiniMax M2.7) — reasoning for Analyser, Fixer, Resolver
- **Python 3.11+** — all agent logic
- **GitHub API** — CI log retrieval, repo cloning
- **Gmail SMTP** — final report delivery
- **pytest** — bug confirmation

---

## Setup

### 1. Clone and install

```bash
git clone https://github.com/Ekaanksh-dev/AutoDebug.git
cd AutoDebug
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install band-sdk
```

### 2. Register 5 agents on Band

Go to [app.band.ai/agents](https://app.band.ai/agents) and create 5 **External Agents**:
`AutoDebug-Detector`, `AutoDebug-Analyser`, `AutoDebug-Fixer`, `AutoDebug-Tester`, `AutoDebug-Resolver`.

Copy each Agent UUID + API Key into `agent_config.yaml`:

```yaml
detector:
  agent_id: "..."
  api_key: "..."
analyser:
  agent_id: "..."
  api_key: "..."
fixer:
  agent_id: "..."
  api_key: "..."
tester:
  agent_id: "..."
  api_key: "..."
resolver:
  agent_id: "..."
  api_key: "..."
```

### 3. Configure `.env`

```bash
cp .env.example .env
nano .env  # fill in your API keys
```

### 4. Start all 5 agents

```bash
autodebug start
autodebug status
```

### 5. Create a Band chat room

In Band, create a chat room and add all 5 agents as participants.

### 6. Trigger detection
@AutoDebug-Detector detect Ekaanksh-dev/test-buggy-repo 27ac9df0... main

Watch the room — each agent responds and hands off to the next automatically.

---

## CLI Reference

| Command | Description |
|---|---|
| `autodebug start` | Launches all 5 agents as background processes |
| `autodebug stop` | Stops all 5 agents |
| `autodebug status` | Shows which agents are running |
| `autodebug doctor` | Validates config files and agent scripts |
| `autodebug detect <repo> <commit> <branch>` | Prints the exact Band mention command to trigger detection |

---

## Local Fallback Mode (no Band)

The original sequential pipeline still works standalone, useful for local testing without Band:

```bash
python main.py analyse --repo owner/repo --commit <sha> --branch main
python main.py test-email
```

---

## Hackathon

Built for the **Band of Agents Hackathon** (June 12–19, 2026)
Track: Multi-Agent Software Development
Platform: [lablab.ai](https://lablab.ai)

---

## License

Copyright 2026 Ekaanksh ([@Ekaanksh-dev](https://github.com/Ekaanksh-dev))

Licensed under the [Apache License 2.0](LICENSE)

---

<p align="center">
Built by Ekaanksh | Powered by Band + NVIDIA API
</p>
