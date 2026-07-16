import Quartz

_dragging = False

def _current_location():
    event = Quartz.CGEventCreate(None)
    return Quartz.CGEventGetLocation(event)

def _clamp_to_display(point):
    bounds = Quartz.CGDisplayBounds(Quartz.CGMainDisplayID())
    x = max(bounds.origin.x, min(point.x, bounds.origin.x + bounds.size.width - 1))
    y = max(bounds.origin.y, min(point.y, bounds.origin.y + bounds.size.height - 1))
    return Quartz.CGPoint(x=x, y=y)

def move_relative(dx: float, dy: float) -> None:
    current = _current_location()
    new_point = Quartz.CGPoint(x=current.x + dx, y=current.y + dy)
    new_point = _clamp_to_display(new_point)
    
    event_type = Quartz.kCGEventLeftMouseDragged if _dragging else Quartz.kCGEventMouseMoved
    button = Quartz.kCGMouseButtonLeft if _dragging else 0

    event = Quartz.CGEventCreateMouseEvent(None, event_type, new_point, button)
    Quartz.CGEventSetIntegerValueField(event, Quartz.kCGMouseEventDeltaX, int(dx))
    Quartz.CGEventSetIntegerValueField(event, Quartz.kCGMouseEventDeltaY, int(dy))
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, event)

def click() -> None:
    current = _current_location()
    down = Quartz.CGEventCreateMouseEvent(None, Quartz.kCGEventLeftMouseDown, current, Quartz.kCGMouseButtonLeft)
    up = Quartz.CGEventCreateMouseEvent(None, Quartz.kCGEventLeftMouseUp, current, Quartz.kCGMouseButtonLeft)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, down)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, up)

def right_click() -> None:
    current = _current_location()
    down = Quartz.CGEventCreateMouseEvent(None, Quartz.kCGEventRightMouseDown, current, Quartz.kCGMouseButtonRight)
    up = Quartz.CGEventCreateMouseEvent(None, Quartz.kCGEventRightMouseUp, current, Quartz.kCGMouseButtonRight)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, down)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, up)

def drag_start() -> None:
    global _dragging
    _dragging = True
    current = _current_location()
    down = Quartz.CGEventCreateMouseEvent(None, Quartz.kCGEventLeftMouseDown, current, Quartz.kCGMouseButtonLeft)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, down)

def drag_move(dx: float, dy: float) -> None:
    # drag_move just calls move_relative which checks _dragging
    move_relative(dx, dy)

def drag_end() -> None:
    global _dragging
    if _dragging:
        _dragging = False
        current = _current_location()
        up = Quartz.CGEventCreateMouseEvent(None, Quartz.kCGEventLeftMouseUp, current, Quartz.kCGMouseButtonLeft)
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, up)

def force_release_all() -> None:
    global _dragging
    if _dragging:
        _dragging = False
        current = _current_location()
        up = Quartz.CGEventCreateMouseEvent(None, Quartz.kCGEventLeftMouseUp, current, Quartz.kCGMouseButtonLeft)
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, up)

def screen_size() -> tuple[int, int]:
    bounds = Quartz.CGDisplayBounds(Quartz.CGMainDisplayID())
    return int(bounds.size.width), int(bounds.size.height)
