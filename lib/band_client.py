import json
import logging
import uuid
from collections import defaultdict
from typing import Callable, Dict, List, Optional

class BandClientWrapper:
    """
    Wrapper around Band SDK's Agent.create() + adapter pattern.
    Connecting to real Band API is mocked for now via phase 1 requirements.
    """
    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self.message_queue: Dict[str, List[dict]] = defaultdict(list)
        
    def create_room(self, room_name: str):
        """Creates a room for collaboration"""
        logging.info(f"Mock: Created room {room_name}")
        
    def add_participant(self, room_id: str, agent_id: str):
        """Adds a participant to an active room"""
        logging.info(f"Mock: Added {agent_id} to room: {room_id}")

    def send_message(self, room_id: str, message: str, mentions: Optional[List[str]] = None):
        """Sends a message with optional mentions"""
        mentions_str = " ".join([f"@{m}" for m in (mentions or [])])
        logging.info(f"Mock: Sent message to {room_id} mentioning {mentions_str}: {message}")

    def subscribe(self, channel: str, handler: Callable):
        """Register a handler for messages on a channel."""
        self.subscribers[channel].append(handler)

    def publish(self, channel: str, message: dict, sender: str):
        """Publish a structured message to a channel with in-memory queue."""
        envelope = {
            "message_id": str(uuid.uuid4())[:8],
            "channel": channel,
            "sender": sender,
            "payload": message,
            "timestamp": "2026-06-14T00:00:00Z"
        }
        self.message_queue[channel].append(envelope)
        logging.info(f"[Band] {sender} -> #{channel}: {json.dumps(message, default=str)}")

    def poll(self, channel: str):
        """Deliver all queued messages on a channel to registered subscribers."""
        while self.message_queue[channel]:
            msg = self.message_queue[channel].pop(0)
            for handler in self.subscribers[channel]:
                handler(msg)