"""Simple notification center used by pages to broadcast backend events to UI subscribers.

Subscribers should implement either `backend_event_notification(event_type, message)` or
`add_notification(message)`. Notifications are delivered on the subscriber's Tk mainloop
via `after(0, ...)` when possible.
"""
from typing import List

_subscribers: List[object] = []


def register(subscriber: object) -> None:
    try:
        if subscriber not in _subscribers:
            _subscribers.append(subscriber)
    except Exception:
        pass


def unregister(subscriber: object) -> None:
    try:
        if subscriber in _subscribers:
            _subscribers.remove(subscriber)
    except Exception:
        pass


def notify(event_type: str, message: str) -> None:
    """Broadcast an event to all registered subscribers.

    Delivery attempts to call `subscriber.backend_event_notification(event_type, message)`.
    If that doesn't exist, falls back to `subscriber.add_notification(message)`.
    Calls are scheduled on the subscriber Tk `after(0, ...)` when available.
    """
    for sub in list(_subscribers):
        try:
            # Prefer backend_event_notification
            fn = getattr(sub, 'backend_event_notification', None)
            if callable(fn):
                try:
                    aft = getattr(sub, 'after', None)
                    if callable(aft):
                        try:
                            aft(0, lambda f=fn, et=event_type, m=message: f(et, m))
                        except Exception:
                            try:
                                fn(event_type, message)
                            except Exception:
                                pass
                    else:
                        try:
                            fn(event_type, message)
                        except Exception:
                            pass
                except Exception:
                    pass
                continue
            # Fallback to add_notification(message)
            fn2 = getattr(sub, 'add_notification', None)
            if callable(fn2):
                try:
                    aft = getattr(sub, 'after', None)
                    if callable(aft):
                        try:
                            aft(0, lambda f=fn2, m=message: f(m))
                        except Exception:
                            try:
                                fn2(message)
                            except Exception:
                                pass
                    else:
                        try:
                            fn2(message)
                        except Exception:
                            pass
                except Exception:
                    pass
        except Exception:
            # Do not let one failed subscriber stop others
            pass
