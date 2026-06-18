# AutoDebug — Multi-Agent Bug Fixing System
# Copyright 2026 Ekaanksh (github.com/Ekaanksh-dev)
# Licensed under Apache License 2.0

import os
import json
import time
from datetime import datetime
from dotenv import load_dotenv
from rich.console import Console

load_dotenv()
console = Console()


class BandClient:
    """
    Communication layer between all 5 agents.
    Before June 12 → uses local JSON file as message queue.
    After June 12  → swap to real Band API (change _send + _receive only).
    """

    QUEUE_FILE = ".band_queue.json"

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.band_api_key = os.getenv("BAND_API_KEY")
        self.room_id = os.getenv("BAND_ROOM_ID")
        self.use_band = False

        if self.use_band:
            console.print(f"[green]✅ {agent_name} connected to Band API[/green]")
        else:
            console.print(f"[yellow]⚡ {agent_name} using local queue (Band API not set)[/yellow]")

    # ── Send message to next agent ────────────────────

    def send(self, to_agent: str, context: dict) -> bool:
        """Send context to next agent"""
        message = {
            "from": self.agent_name,
            "to": to_agent,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "context": context
        }

        if self.use_band:
            return self._send_band(message)
        else:
            return self._send_local(message)

    # ── Receive message from previous agent ───────────

    def receive(self, timeout: int = 30) -> dict:
        """Wait for and receive context from previous agent"""
        if self.use_band:
            return self._receive_band(timeout)
        else:
            return self._receive_local(timeout)

    # ── Local queue (used before June 12) ────────────

    def _send_local(self, message: dict) -> bool:
        try:
            queue = self._load_queue()
            queue.append(message)
            self._save_queue(queue)
            console.print(f"[blue]📨 {self.agent_name} → {message['to']}[/blue]")
            return True
        except Exception as e:
            console.print(f"[red]❌ Send failed: {e}[/red]")
            return False

    def _receive_local(self, timeout: int = 120) -> dict:
        start = time.time()
        while time.time() - start < timeout:
            queue = self._load_queue()
            for i, msg in enumerate(queue):
                if msg["to"] == self.agent_name:
                    queue.pop(i)
                    self._save_queue(queue)
                    console.print(f"[green]📩 {self.agent_name} received from {msg['from']}[/green]")
                    return msg["context"]
            time.sleep(0.5)
        console.print(f"[red]⏰ {self.agent_name} timed out waiting for message[/red]")
        return {}

    def _load_queue(self) -> list:
        try:
            with open(self.QUEUE_FILE, "r") as f:
                return json.load(f)
        except:
            return []

    def _save_queue(self, queue: list):
        with open(self.QUEUE_FILE, "w") as f:
            json.dump(queue, f, indent=2)

    # ── Real Band API (swap in on June 12) ────────────

    def _send_band(self, message: dict) -> bool:
        try:
            import requests
            response = requests.post(
                "https://api.band.us/v2/band/message/create",
                headers={"Authorization": f"Bearer {self.band_api_key}"},
                json={
                    "band_key": self.room_id,
                    "content": json.dumps(message)
                }
            )
            return response.status_code == 200
        except Exception as e:
            console.print(f"[red]❌ Band API error: {e}[/red]")
            return False

    def _receive_band(self, timeout: int = 30) -> dict:
        # TODO: implement Band API polling on June 12
        # Replace with real Band API receive logic
        return self._receive_local(timeout)

    def log(self, message: str):
        """Log agent activity"""
        console.print(f"[cyan][{self.agent_name}][/cyan] {message}")
