import asyncio
import logging
from typing import Callable, Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class EventHub:
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def init(self, loop: asyncio.AbstractEventLoop):
        self._loop = loop

    def subscribe(self, topic: str, handler: Callable):
        if topic not in self._subscribers:
            self._subscribers[topic] = []
        if handler not in self._subscribers[topic]:
            self._subscribers[topic].append(handler)
        logger.debug(f"Subscribed to {topic}")

    def unsubscribe(self, topic: str, handler: Callable):
        if topic in self._subscribers:
            if handler in self._subscribers[topic]:
                self._subscribers[topic].remove(handler)
                logger.debug(f"Unsubscribed from {topic}")

    def unsubscribe_all(self):
        self._subscribers.clear()

    def send_all_on_topic(self, topic: str, message: Any):
        # logger.debug(f"Sending on topic {topic}: {message}")
        if topic in self._subscribers:
            # Create a copy of the list to avoid modification during iteration
            handlers = self._subscribers[topic][:]
            for handler in handlers:
                try:
                    if self._loop:
                        # Check if we are in the loop
                        try:
                            current_loop = asyncio.get_running_loop()
                        except RuntimeError:
                            current_loop = None
                        
                        if current_loop == self._loop:
                            # We are in the loop
                            if asyncio.iscoroutinefunction(handler):
                                self._loop.create_task(handler(topic, message))
                            else:
                                handler(topic, message)
                        else:
                            # We are in another thread
                            if asyncio.iscoroutinefunction(handler):
                                asyncio.run_coroutine_threadsafe(handler(topic, message), self._loop)
                            else:
                                self._loop.call_soon_threadsafe(handler, topic, message)
                    else:
                        # No loop configured, just run it (might fail for async)
                        if asyncio.iscoroutinefunction(handler):
                             logger.warning(f"EventHub loop not initialized. Cannot dispatch async handler for {topic}")
                        else:
                            handler(topic, message)
                except Exception as e:
                    logger.error(f"Error handling message on topic {topic}: {e}")

# Global instance
event_hub = EventHub()

def init_event_hub(loop):
    """Initialize the global event hub with the given loop."""
    event_hub.init(loop)
