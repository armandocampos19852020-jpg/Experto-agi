from __future__ import annotations

import json
import os
import time
from datetime import datetime
from typing import Any

import requests


class Config:
    github_token = os.getenv("TOKEN", "")
    repo_owner = os.getenv("REPO_OWNER", "")
    repo_name = os.getenv("REPO_NAME", "")
    hook_id = os.getenv("HOOK_ID", "")

    nvidia_cosmos_url = os.getenv(
        "NVIDIA_COSMOS_URL",
        "https://api.nvidia.com/v1/cosmos/reasoning",
    )
    nvidia_api_key = os.getenv("NVIDIA_API_KEY", "")

    poll_seconds = int(os.getenv("POLL_SECONDS", "300"))


class CosmosSentry:
    def __init__(self) -> None:
        self.github_headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {Config.github_token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        self.headers_nv = {
            "Authorization": f"Bearer {Config.nvidia_api_key}",
            "Content-Type": "application/json",
        }

    def _check_required_env(self) -> tuple[bool, str]:
        required = {
            "TOKEN": Config.github_token,
            "REPO_OWNER": Config.repo_owner,
            "REPO_NAME": Config.repo_name,
            "HOOK_ID": Config.hook_id,
        }
        missing = [k for k, v in required.items() if not v]
        if missing:
            return False, f"Missing env vars: {', '.join(missing)}"
        return True, "ok"

    def get_failed_deliveries(self) -> list[dict[str, Any]]:
        if not Config.github_token:
            return []

        url = (
            f"https://api.github.com/repos/{Config.repo_owner}/{Config.repo_name}"
            f"/hooks/{Config.hook_id}/deliveries"
        )
        response = requests.get(url, headers=self.github_headers, timeout=20)
        response.raise_for_status()
        deliveries = response.json() or []

        failed = []
        for delivery in deliveries:
            status = str(delivery.get("status", "")).upper()
            if status != "OK":
                failed.append(delivery)
        return failed

    def reason_with_cosmos(self, error_payload: Any) -> str:
        if not Config.nvidia_api_key:
            return "NVIDIA_API_KEY not set; skipping Cosmos reasoning"

        payload = {
            "model": "cosmos-reason-2",
            "messages": [
                {
                    "role": "user",
                    "content": f"Analyze this failed webhook payload and suggest remediation: {json.dumps(error_payload, default=str)}",
                }
            ],
            "acceleration": "nvidia-gpu-fp8",
        }

        try:
            response = requests.post(
                Config.nvidia_cosmos_url,
                json=payload,
                headers=self.headers_nv,
                timeout=30,
            )
            if response.ok:
                return "Cosmos reasoning completed"
            return f"Cosmos request failed ({response.status_code})"
        except Exception as exc:
            return f"Cosmos request error: {exc}"

    def execute_redelivery(self, delivery_id: int) -> None:
        if not Config.github_token:
            return

        url = (
            f"https://api.github.com/repos/{Config.repo_owner}/{Config.repo_name}"
            f"/hooks/{Config.hook_id}/deliveries/{delivery_id}/attempts"
        )
        response = requests.post(url, headers=self.github_headers, timeout=20)
        response.raise_for_status()
        print(f"[ACTION] Redelivery triggered for delivery_id={delivery_id}")

    def run_forever(self) -> None:
        print("[START] cosmos_pitbull_sentry online")

        while True:
            ok, msg = self._check_required_env()
            if not ok:
                print(f"[WARN] {msg}. Sleeping 60s")
                time.sleep(60)
                continue

            try:
                failed = self.get_failed_deliveries()
                if not failed:
                    print(f"[OK] {datetime.now().isoformat()} no failed deliveries")
                else:
                    for delivery in failed:
                        request_obj = delivery.get("request") or {}
                        payload = request_obj.get("payload")
                        reasoning = self.reason_with_cosmos(payload)
                        print(f"[INFO] {reasoning}")

                        delivery_id = delivery.get("id")
                        if isinstance(delivery_id, int):
                            self.execute_redelivery(delivery_id)
                        else:
                            print("[WARN] delivery id missing; skipping redelivery")

                time.sleep(max(Config.poll_seconds, 30))
            except Exception as exc:
                print(f"[ERROR] loop failure: {exc}")
                time.sleep(60)


if __name__ == "__main__":
    CosmosSentry().run_forever()
