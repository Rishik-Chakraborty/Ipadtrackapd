import pytest
from server.ws_server import DISPATCH_TABLE
from server.input.backend import RecordingBackend

def test_ws_dispatch():
    backend = RecordingBackend()
    
    # Test move
    DISPATCH_TABLE["move"](backend, {"dx": 5, "dy": -3})
    assert backend.calls[-1] == ("move_relative", (5, -3))
    
    # Test click
    DISPATCH_TABLE["click"](backend, {"button": "left"})
    assert backend.calls[-1] == ("click", ())
    
    # Test scroll
    DISPATCH_TABLE["scroll"](backend, {"dx": 0, "dy": 10, "phase": "changed"})
    assert backend.calls[-1] == ("scroll", (0, 10, "changed"))
    
    # Test zoom
    DISPATCH_TABLE["zoom"](backend, {"scale": 1.2, "phase": "changed"})
    assert backend.calls[-1] == ("zoom", (1.2, "changed"))
    
    # Test swipe3
    DISPATCH_TABLE["swipe3"](backend, {"direction": "up"})
    assert backend.calls[-1] == ("swipe", (3, "up"))

def test_smoke_import_app():
    # Trivial smoke test to ensure no import-time crashes (like __dirname__)
    import server.app
    assert server.app is not None
