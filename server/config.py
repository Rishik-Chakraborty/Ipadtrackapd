import os

PORT = int(os.environ.get("IPADTRACKAPD_PORT", 8765))
HTTP_HOST = "0.0.0.0"
SERVICE_NAME = "Ipadtrackapd"
ZEROCONF_TYPE = "_trackpad._tcp.local."
INVERT_SCROLL = os.environ.get("IPADTRACKAPD_INVERT_SCROLL", "0") == "1"
SCROLL_UNIT_PIXELS = True
ZOOM_SCROLL_GAIN = 8.0          # scale-delta -> synthetic scroll-dy multiplier, tuned by feel
LOG_LEVEL = os.environ.get("IPADTRACKAPD_LOG_LEVEL", "INFO")

# macOS virtual keycodes (see HIToolbox/Events.h)
KC_LEFT, KC_RIGHT, KC_DOWN, KC_UP = 123, 124, 125, 126

SWIPE_KEYCODE_MAP = {
    3: {
        "up":    (KC_UP,   "control"),   # Mission Control
        "down":  (KC_DOWN, "control"),   # App Exposé
        "left":  (KC_LEFT, "control"),   # Space left
        "right": (KC_RIGHT,"control"),   # Space right
    },
    4: {
        "left":  (KC_LEFT, "control"),
        "right": (KC_RIGHT,"control"),
    },
}
