from typing import Dict, Any

class BotState:
    last_network_status: str = "OK"
    pending_actions: Dict[int, Dict[str, Any]] = {}

bot_state = BotState()