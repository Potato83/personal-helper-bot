from aiogram import BaseMiddleware
from aiogram.types import Message
from typing import Callable, Dict, Any, Awaitable

class PrivateBotMiddleware(BaseMiddleware):
    def __init__(self, allowed_id: int):
        self.allowed_id = allowed_id

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        # checking user
        if event.from_user.id != self.allowed_id:
            # if not ur bot - ingore
            return 
        
        # else - work!
        return await handler(event, data)