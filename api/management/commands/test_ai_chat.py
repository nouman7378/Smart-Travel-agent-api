from __future__ import annotations

import json
from typing import List, Optional

from django.core.management.base import BaseCommand, CommandError
from django.test import Client


class Command(BaseCommand):
    """Send a sample conversation to /api/ai/chat/ to verify the AI stack."""

    help = (
        "Exercises the AI chat endpoint with a configurable series of messages "
        "and prints the assistant responses so you can verify the integration."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--messages",
            nargs="+",
            help="Custom list of user utterances to send to the chat endpoint",
        )
        parser.add_argument(
            "--show-context",
            action="store_true",
            help="Print the context object returned by the backend after each turn.",
        )
        parser.add_argument(
            "--show-recommendations",
            action="store_true",
            help="Pretty-print any recommendation payloads from the response.",
        )

    def handle(self, *args, **options) -> None:
        messages: List[str] = options.get("messages") or [
            "Hi, I'm planning a trip to Murree soon.",
            "My budget is 1500 dollars for two adults.",
            "Can you suggest an itinerary or package?",
        ]

        client = Client()
        session_id: Optional[str] = None

        self.stdout.write(self.style.NOTICE("--- Starting AI chat smoke test ---"))

        for turn, user_message in enumerate(messages, start=1):
            payload = {"message": user_message}
            if session_id:
                payload["sessionId"] = session_id

            response = client.post(
                "/api/ai/chat/",
                data=json.dumps(payload),
                content_type="application/json",
            )

            try:
                data = response.json()
            except ValueError as exc:  # pragma: no cover - defensive logging
                raise CommandError(
                    f"Turn {turn}: non-JSON response {response.status_code}: {response.content[:200]!r}"
                ) from exc

            if response.status_code != 200 or not data.get("success"):
                raise CommandError(
                    f"Turn {turn}: backend returned an error {response.status_code}: {json.dumps(data, indent=2)}"
                )

            session_id = data.get("sessionId", session_id)
            assistant_message = data.get("message", "<no message>")

            self.stdout.write(self.style.SUCCESS(f"[{turn}] User -> {user_message}"))
            self.stdout.write(self.style.HTTP_INFO(f"[{turn}] Assistant -> {assistant_message}"))

            if options.get("show_context") and data.get("context"):
                pretty_context = json.dumps(data["context"], indent=2)
                self.stdout.write(self.style.SQL_FIELD(f"Context:\n{pretty_context}"))

            if options.get("show_recommendations") and data.get("recommendations"):
                pretty_reco = json.dumps(data["recommendations"], indent=2)
                self.stdout.write(self.style.SQL_FIELD(f"Recommendations:\n{pretty_reco}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Chat smoke test finished successfully (sessionId={session_id or 'N/A'})."
            )
        )
