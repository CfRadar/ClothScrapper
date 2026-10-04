import asyncio
import sys


def event_loop_factory():
    """Returns a ProactorEventLoop on Windows so asyncio subprocesses (Playwright) work."""
    if sys.platform == "win32":
        return asyncio.ProactorEventLoop()
    return asyncio.new_event_loop()
