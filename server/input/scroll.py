import Quartz
from server import config

def scroll(dx: float, dy: float, phase: str = "changed") -> None:
    if config.INVERT_SCROLL:
        dx = -dx
        dy = -dy
    
    event = Quartz.CGEventCreateScrollWheelEvent2(None, Quartz.kCGScrollEventUnitPixel, 2, int(dy), int(dx), 0)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, event)
