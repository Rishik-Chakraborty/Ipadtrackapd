import Quartz
from server import config

KEYCODE_MODIFIER_FLAGS = {
    "control": Quartz.kCGEventFlagMaskControl,
    "command": Quartz.kCGEventFlagMaskCommand
}

def send_shortcut(keycode: int, modifier: str | None = None) -> None:
    flags = KEYCODE_MODIFIER_FLAGS.get(modifier, 0) if modifier else 0
    down = Quartz.CGEventCreateKeyboardEvent(None, keycode, True)
    up = Quartz.CGEventCreateKeyboardEvent(None, keycode, False)
    
    if flags:
        Quartz.CGEventSetFlags(down, flags)
        Quartz.CGEventSetFlags(up, flags)
        
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, down)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, up)

def swipe(fingers: int, direction: str) -> None:
    mapping = config.SWIPE_KEYCODE_MAP.get(fingers, {}).get(direction)
    if mapping:
        send_shortcut(*mapping)
