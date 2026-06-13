import logging
from typing import List, Optional

class BandClientWrapper:
    """
    Wrapper around Band SDK's Agent.create() + adapter pattern.
    Connecting to real Band API is mocked for now via phase 1 requirements.
    """
    def __init__(self):
        # self.client = client
        pass
        
    def create_room(self, room_name: str):
        """Creates a room for collaboration"""
        # return self.client.create_room(room_name)
        logging.info(f"Mock: Created room {room_name}")
        
    def add_participant(self, room_id: str, agent_id: str):
        """Adds a participant to an active room"""
        # self.client.add_participant(room_id, agent_id)
        logging.info(f"Mock: Added {agent_id} to room: {room_id}")

    def send_message(self, room_id: str, message: str, mentions: Optional[List[str]] = None):
        """Sends a message with optional mentions"""
        # self.client.send_message(room_id, message, mentions)
        mentions_str = " ".join([f"@{m}" for m in (mentions or [])])
        logging.info(f"Mock: Sent message to {room_id} mentioning {mentions_str}: {message}")