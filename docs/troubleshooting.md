# AutoDebug — Build Problems & Fixes

A log of real issues encountered while building the Band-native multi-agent pipeline.

## 1. GitHub Actions log was binary ZIP, parsed as text
**Symptom:** Detector always returned "no errors found" even on failed CI runs.
**Cause:** `requests.get(logs_url).text` was being called on a ZIP archive response, not plain text.
**Fix:** Switched to the per-job logs endpoint (`/actions/jobs/{id}/logs`), which returns plain text directly.

## 2. Band send/receive routed to different channels
**Symptom:** Detector logged "Bug detected" but Analyser timed out with "No data received."
**Cause:** `use_band` flag was true (real Band API key set), so `send()` posted to `api.band.us` (the social network, wrong product) while `receive()` still read from the local JSON queue. Messages went nowhere.
**Fix:** Forced `use_band = False` temporarily until the real Band SDK was integrated.

## 3. Threaded agents timed out before message arrived
**Symptom:** Detector finished and sent its message, but Analyser had already timed out and exited.
**Cause:** All 5 agents started simultaneously as threads. Detector's clone + scan took 30-60s; Analyser's wait timeout was shorter.
**Fix:** Switched `pipeline.py` from threaded to sequential agent calls for the local-queue version.

## 4. Absolute path stored instead of relative path
**Symptom:** Tester's `os.path.exists(full_path)` returned `False` even though the file existed.
**Cause:** `bug_file` held the full clone path (`/tmp/repo_name/broken.py`), then got joined with `clone_path` again, doubling the path.
**Fix:** Strip the clone path prefix in `extract_bug_from_log()` before storing `bug_file`.

## 5. Tester only checked pytest output, not direct execution
**Symptom:** `confirm_bug_exists()` always returned `False` — "no tests ran in 0.00s."
**Cause:** Test repo had no pytest test files, only a script that crashes on import/run.
**Fix:** Added a fallback that directly executes the buggy file and checks `stderr` for the error type when pytest finds nothing.

## 6. DevOps Notifier dispatch failed with HTTP 422
**Symptom:** `Invalid request. No more than 10 properties are allowed; 16 were supplied.`
**Cause:** `client_payload` had 16 keys; GitHub's `repository_dispatch` API caps it at 10.
**Fix:** Trimmed payload to exactly 10 fields.

## 7. Reasoning model returned `content: None`
**Symptom:** Agent functions crashed or returned `None` from `response.choices[0].message.content`.
**Cause:** MiniMax M2.7 (via NVIDIA API) is a reasoning model — it writes to `reasoning_content` first, then `content`. With `max_tokens=50` it ran out of budget before finishing the reasoning step.
**Fix:** Read `msg.content or msg.reasoning_content`, increased `max_tokens` to 2048.

## 8. pip blocked by Arch's externally-managed-environment
**Symptom:** `error: externally-managed-environment` on every `pip install`.
**Cause:** PEP 668 — Arch blocks system-wide pip installs.
**Fix:** Created and activated a venv before any pip command.

## 9. Local `band/` folder shadowed the real Band SDK
**Symptom:** `from band import Agent` resolved to our own empty local module instead of the installed `band-sdk` package.
**Cause:** Project folder was named `band/`, identical to the installed package name.
**Fix:** Renamed to `band_local/`, updated all imports across the 5 local-queue agents.

## 10. Wrong mental model of Band's architecture
**Symptom:** Spent hours hitting `api.band.us/v2/band/message/create` with no success.
**Cause:** Assumed Band was a message queue / pub-sub system. It's actually a chat-room platform — agents connect via WebSocket and respond to @mentions using `SimpleAdapter.on_message()`.
**Fix:** Read the actual SDK docs, rewrote all 5 agents as `SimpleAdapter` subclasses registered on app.band.ai, communicating via @mentions in a shared room.

## 11. Indentation bug: `return` outside the `if` block
**Symptom:** Fixer, Tester, and Resolver agents silently did nothing when a valid command message arrived.
**Cause:** In each `on_message()`, the command-check pattern was:
```python
if "fix" not in text.split():
    print("NO FIX COMMAND FOUND")
return  # ← outside the if, runs unconditionally
```
**Fix:** Corrected indentation so `return` is inside the `if` block.

## 12. Full JSON context visible in chat room
**Known limitation, not fixed:** Each agent hands off context as raw JSON appended to the @mention text (e.g. `analyse {...}`), including `raw_code` and `surrounding_code`. This works but is noisy for anyone watching the room. A cleaner version would store context via Band's structured memory and only post human-readable status lines.

## 13. Email + DevOps Notifier — confirmed working
Resolved. `send_email()` and `trigger_devops_notifier()` both fire successfully on a confirmed bug, verified via direct inbox screenshot.

## 14. Repo cleanup
Excluded from git via `.gitignore`: `venv/`, `.env`, `agent_config.yaml`, `logs/*.log`, `__pycache__/`.

## 15. Fallback Mode

`band_local/` contains a local JSON queue implementation that acts as a 
drop-in replacement for Band when:
- Band API key is unavailable or rate-limited  
- Running locally without internet access
- Development and testing without Band credentials

To use fallback mode, set `use_band = False` in `band_local/client.py`.
The pipeline logic remains identical — only the message transport changes.
