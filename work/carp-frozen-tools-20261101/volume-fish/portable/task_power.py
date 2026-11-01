"""Prevent automatic system sleep only while a local production job runs.

Display timeout and saved power-plan settings are untouched. Explicit user sleep
and shutdown are not blocked. The OS clears the request if this process exits.
"""
import os
from contextlib import contextmanager

@contextmanager
def keep_system_awake(api=None):
    if api is None and os.name != 'nt':
        yield
        return
    if api is None:
        import ctypes
        api=ctypes.windll.kernel32.SetThreadExecutionState
    old=api(0x80000001)  # ES_CONTINUOUS | ES_SYSTEM_REQUIRED; no display request.
    if not old:
        raise OSError('Windows rejected the task-scoped sleep prevention request')
    try:
        yield
    finally:
        api(old)
