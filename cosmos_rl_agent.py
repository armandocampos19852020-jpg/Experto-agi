import json
import os
import time
from datetime import datetime

import torch
from octokit import Octokit


class ApexConfig:
    """Configuration loaded from environment variables."""

    TOKEN = os.getenv("TOKEN")
    REPO_OWNER = os.getenv("REPO_OWNER")
    REPO_NAME = os.getenv("REPO_NAME")
    HOOK_ID = os.getenv("HOOK_ID")

    # Kept as metadata; octokit API calls are unaffected by tensor precision.
    PRECISION = "fp8"
    LOG_FILE = "cosmos_brain_memory.json"


class CosmosRLAgent:
    def __init__(self) -> None:
        self._validate_config()
        self.octokit = Octokit(auth=ApexConfig.TOKEN)
        self.memory = self.load_memory()

        # Lightweight tensor just to demonstrate adaptive state on GPU/CPU.
        self.brain = torch.tensor(
            [1.0, 5.0, 10.0],
            device="cuda" if torch.cuda.is_available() else "cpu",
        )

    def _validate_config(self) -> None:
        required = {
            "TOKEN": ApexConfig.TOKEN,
            "REPO_OWNER": ApexConfig.REPO_OWNER,
            "REPO_NAME": ApexConfig.REPO_NAME,
            "HOOK_ID": ApexConfig.HOOK_ID,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise ValueError(
                "Missing environment variables: " + ", ".join(missing)
            )

    def load_memory(self) -> dict:
        if os.path.exists(ApexConfig.LOG_FILE):
            try:
                with open(ApexConfig.LOG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    return data
            except (json.JSONDecodeError, OSError):
                pass

        return {"success_count": 0, "fail_count": 0, "optimal_wait": 300}

    def save_memory(self) -> None:
        with open(ApexConfig.LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.memory, f, ensure_ascii=True, indent=2)

    def get_deliveries(self) -> list:
        url = (
            f"/repos/{ApexConfig.REPO_OWNER}/"
            f"{ApexConfig.REPO_NAME}/hooks/{ApexConfig.HOOK_ID}/deliveries"
        )
        response = self.octokit.request("GET", url)
        return response.data

    def learn_from_result(self, success: bool) -> None:
        """Adjust retry policy with a simple reward/penalty strategy."""
        if success:
            self.memory["success_count"] += 1
            self.memory["optimal_wait"] = max(60, self.memory["optimal_wait"] - 10)
        else:
            self.memory["fail_count"] += 1
            self.memory["optimal_wait"] += 30
        self.save_memory()

    def execute_logic(self) -> None:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        print(f"--- Apex Sentry Loop [{now}] ---")

        try:
            deliveries = self.get_deliveries()
        except Exception as exc:
            print(f"Failed to fetch deliveries: {exc}")
            self.learn_from_result(False)
            return

        failed = [d for d in deliveries if d.get("status") != "OK"]

        if not failed:
            print("Status: Alpha Clear. All systems nominal.")
            return

        for delivery in failed:
            delivery_id = delivery.get("id")
            print(f"Detected failed delivery ID: {delivery_id}. Running recovery...")

            try:
                url_post = (
                    f"/repos/{ApexConfig.REPO_OWNER}/"
                    f"{ApexConfig.REPO_NAME}/hooks/{ApexConfig.HOOK_ID}/"
                    f"deliveries/{delivery_id}/attempts"
                )
                self.octokit.request("POST", url_post)
                print(f"Redelivery triggered for {delivery_id}.")
                self.learn_from_result(True)
            except Exception as exc:
                print(f"Critical redelivery failure for {delivery_id}: {exc}")
                self.learn_from_result(False)

    def run_24_7(self) -> None:
        while True:
            self.execute_logic()
            wait = self.memory["optimal_wait"]
            print(f"Sleeping {wait}s (adapted by RL memory).")
            time.sleep(wait)


if __name__ == "__main__":
    agent = CosmosRLAgent()
    agent.run_24_7()
