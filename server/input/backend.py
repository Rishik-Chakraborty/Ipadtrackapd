from typing import Protocol
import sys
from ApplicationServices import AXIsProcessTrustedWithOptions, kAXTrustedCheckOptionPrompt
from server.input import mouse, scroll, zoom, keyboard

class InputBackend(Protocol):
    def move_relative(self, dx: float, dy: float) -> None: ...
    def click(self) -> None: ...
    def right_click(self) -> None: ...
    def drag_start(self, fingers: int) -> None: ...
    def drag_move(self, dx: float, dy: float) -> None: ...
    def drag_end(self) -> None: ...
    def scroll(self, dx: float, dy: float, phase: str) -> None: ...
    def zoom(self, scale: float, phase: str) -> None: ...
    def swipe(self, fingers: int, direction: str) -> None: ...
    def force_release_all(self) -> None: ...
    def screen_size(self) -> tuple[int, int]: ...


class QuartzBackend:
    def move_relative(self, dx: float, dy: float) -> None:
        mouse.move_relative(dx, dy)
        
    def click(self) -> None:
        mouse.click()
        
    def right_click(self) -> None:
        mouse.right_click()
        
    def drag_start(self, fingers: int) -> None:
        mouse.drag_start()
        
    def drag_move(self, dx: float, dy: float) -> None:
        mouse.drag_move(dx, dy)
        
    def drag_end(self) -> None:
        mouse.drag_end()
        
    def scroll(self, dx: float, dy: float, phase: str) -> None:
        scroll.scroll(dx, dy, phase)
        
    def zoom(self, scale: float, phase: str) -> None:
        zoom.apply(scale, phase)
        
    def swipe(self, fingers: int, direction: str) -> None:
        keyboard.swipe(fingers, direction)
        
    def force_release_all(self) -> None:
        mouse.force_release_all()
        
    def screen_size(self) -> tuple[int, int]:
        return mouse.screen_size()


class RecordingBackend:
    def __init__(self):
        self.calls = []

    def move_relative(self, dx: float, dy: float) -> None:
        self.calls.append(("move_relative", (dx, dy)))

    def click(self) -> None:
        self.calls.append(("click", ()))

    def right_click(self) -> None:
        self.calls.append(("right_click", ()))

    def drag_start(self, fingers: int) -> None:
        self.calls.append(("drag_start", (fingers,)))

    def drag_move(self, dx: float, dy: float) -> None:
        self.calls.append(("drag_move", (dx, dy)))

    def drag_end(self) -> None:
        self.calls.append(("drag_end", ()))

    def scroll(self, dx: float, dy: float, phase: str) -> None:
        self.calls.append(("scroll", (dx, dy, phase)))

    def zoom(self, scale: float, phase: str) -> None:
        self.calls.append(("zoom", (scale, phase)))

    def swipe(self, fingers: int, direction: str) -> None:
        self.calls.append(("swipe", (fingers, direction)))

    def force_release_all(self) -> None:
        self.calls.append(("force_release_all", ()))

    def screen_size(self) -> tuple[int, int]:
        self.calls.append(("screen_size", ()))
        return (1920, 1080)


def preflight_accessibility() -> bool:
    options = {kAXTrustedCheckOptionPrompt: True}
    trusted = AXIsProcessTrustedWithOptions(options)
    if not trusted:
        print("="*60)
        print("ACCESSIBILITY PERMISSION REQUIRED")
        print("Please grant Accessibility access to:")
        print(sys.executable)
        print("\nGo to: System Settings -> Privacy & Security -> Accessibility")
        print("="*60)
    return trusted
