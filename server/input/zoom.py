import Quartz
from server import config

def apply(scale: float, phase: str = "changed") -> None:
    dy = (scale - 1.0) * config.ZOOM_SCROLL_GAIN
    event = Quartz.CGEventCreateScrollWheelEvent2(None, Quartz.kCGScrollEventUnitPixel, 2, int(dy), 0, 0)
    Quartz.CGEventSetFlags(event, Quartz.kCGEventFlagMaskCommand)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, event)
