"""Simple decoupled pub-sub event bus for application state synchronization."""

from typing import Callable, Dict, List, Any


class EventBus:
    """Thread-safe, synchronous pub-sub event bus."""

    def __init__(self) -> None:
        self._listeners: Dict[str, List[Callable[[Any], None]]] = {}

    def subscribe(self, event_type: str, callback: Callable[[Any], None]) -> None:
        """Register a callback for an event type."""
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        if callback not in self._listeners[event_type]:
            self._listeners[event_type].append(callback)

    def unsubscribe(self, event_type: str, callback: Callable[[Any], None]) -> None:
        """Unregister a callback for an event type."""
        if event_type in self._listeners:
            try:
                self._listeners[event_type].remove(callback)
            except ValueError:
                pass

    def emit(self, event_type: str, payload: Any = None) -> None:
        """Notify all subscribers listening to event_type."""
        for callback in list(self._listeners.get(event_type, [])):
            try:
                callback(payload)
            except Exception as e:
                # Keep bus resilient against single callback errors
                print(f"[EventBus] Error executing subscriber for '{event_type}': {e}")

    def clear(self) -> None:
        """Clear all registered event listeners."""
        self._listeners.clear()


# Default singleton event bus instance for presentation-application decoupling
event_bus = EventBus()
