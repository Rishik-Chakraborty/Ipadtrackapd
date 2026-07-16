# iPad-as-Trackpad for Mac (Ipadtrackapd)

## Context

The repo is currently empty (just a placeholder `main.py` from `git init`, to be deleted). The goal: use an iPad as a wireless trackpad for a Mac, saving desk space vs. an Apple trackpad, with full gesture parity (move, click, scroll, right-click, drag, pinch-zoom, multi-finger swipes) **and real haptic feedback** from v1.

Confirmed decisions (via user Q&A):
- iPad UI is a **web app** (HTML/CSS/JS) served by the Mac — no App Store, no complex signing pipeline, no build tooling.
- Transport is **WebSocket over local Wi-Fi** (same LAN, no cloud relay, no USB).
- Discovery via **mDNS `.local` hostname + QR code** (browsers can't browse raw mDNS, so `.local` DNS resolution + a scannable QR code is the practical pairing UX).
- Mac server is **Python** (aiohttp), injecting events via **pyobjc/Quartz** (user has agreed to grant Accessibility permission).
- Mac server runs as a **manually-started process** for v1 (no login item/menu bar yet).
- **Haptic feedback requirement forced one architecture change**: iOS Safari has never implemented the Vibration API (`navigator.vibrate`), even for home-screen PWAs — there is no way to trigger the Taptic Engine from a pure web page on iPadOS. To get real haptics, the same web code is loaded inside a **thin native WKWebView wrapper app** (`ios-app/`) built in Xcode, which exposes a JS→native bridge that calls `UIImpactFeedbackGenerator` / `UISelectionFeedbackGenerator` / `UINotificationFeedbackGenerator`. This is intentionally minimal (~150-200 lines of Swift, a WebView and a message handler, nothing else) — everything else (gesture logic, protocol, rendering) still lives in the shared web code and is unaffected. The web app still degrades gracefully (haptics silently no-op) if opened in plain Safari instead of the wrapper.

## Repository Structure

```
Ipadtrackapd/
├── requirements.txt
├── requirements-dev.txt        # pytest, for the one testable seam
├── README.md
├── scripts/run.sh              # venv setup + `python -m server.main`
├── docs/
│   ├── PROTOCOL.md             # source of truth for the WS JSON schema
│   └── HAPTICS.md              # JS<->native bridge message schema
├── server/                     # Python (Mac side)
│   ├── __init__.py
│   ├── main.py                 # entrypoint: aiohttp app + mDNS advertiser + QR/URL printer
│   ├── config.py                # PORT, INVERT_SCROLL, SWIPE_KEYCODE_MAP, etc.
│   ├── app.py                    # aiohttp Application factory: static routes + /ws + /api/health
│   ├── ws_server.py               # parses JSON envelope, dispatches by `type` to input backend
│   ├── discovery.py                # zeroconf registration + LAN-IP helper + QR printer
│   └── input/
│       ├── __init__.py
│       ├── backend.py               # InputBackend protocol + RecordingBackend + accessibility preflight
│       ├── mouse.py                  # move_relative, click, right_click, drag_start/move/end, force_release_all
│       ├── scroll.py                  # scroll(dx, dy, phase)
│       ├── zoom.py                     # Cmd+scroll fallback for pinch
│       └── keyboard.py                  # keycode shortcut synthesis (Mission Control/Exposé/Spaces)
├── web/                         # static assets, plain ES module JS, no build step/npm
│   ├── index.html
│   ├── css/style.css
│   └── js/
│       ├── config.js               # tunable constants
│       ├── protocol.js              # WS message envelope builders + seq counter
│       ├── touch-tracker.js          # raw touchstart/move/end/cancel capture per identifier
│       ├── gesture-recognizer.js      # finger-count/timing state machine
│       ├── haptics.js                  # JS->native bridge, no-op fallback in plain Safari
│       └── main.js                      # WS lifecycle, status UI, wires everything together
├── ios-app/                     # thin native wrapper, ONLY reason it exists is real haptics
│   ├── Ipadtrackapd.xcodeproj
│   └── Ipadtrackapd/
│       ├── IpadtrackapdApp.swift    # SwiftUI @main entry
│       ├── ContentView.swift          # hosts the web view, holds server URL state
│       ├── WebViewContainer.swift      # UIViewRepresentable wrapping WKWebView + bridge registration
│       ├── HapticsBridge.swift          # WKScriptMessageHandler -> UIFeedbackGenerator calls
│       ├── SettingsView.swift            # editable server URL (fallback if .local resolution fails)
│       └── Info.plist                     # ATS exception for local http://, local network usage string
└── tests/
    └── test_ws_dispatch.py    # pytest against ws_server.py using a RecordingBackend
```

---

## Component 1: Mac Server (`server/`)

### `server/config.py`
Central constants, stdlib only (`os`), every value overridable via `IPADTRACKAPD_*` env vars so the wrapper script/tests can override without editing code.

```python
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
```

### `server/main.py`
Entrypoint. Functions:
- `build_arg_parser() -> argparse.ArgumentParser` — flags `--port`, `--verbose`, `--no-qr`, `--no-mdns`.
- `async def main() -> None` — parses args; configures `logging`; runs `input.backend.preflight_accessibility()` and prints setup instructions if it returns `False` (still continues running so the user can grant permission and reconnect without restarting); builds the `InputBackend` (`QuartzBackend` from `input/*`); builds the aiohttp app via `app.create_app(backend)`; starts `discovery.ZeroconfAdvertiser` (using `zeroconf.asyncio.AsyncZeroconf` so registration doesn't block the aiohttp event loop); calls `discovery.print_connection_info(port)`; starts the server with `web.AppRunner` + `web.TCPSite` (rather than the blocking `web.run_app`) so shutdown can be sequenced manually; registers `signal.SIGINT`/`SIGTERM` handlers that call `backend.force_release_all()` and `advertiser.stop()` before exiting, guaranteeing no stuck mouse button and a clean mDNS unregister on Ctrl-C.
- `def run() -> None` — `asyncio.run(main())`; wired as `python -m server.main`.

### `server/app.py`
- `create_app(backend: InputBackend) -> web.Application` — `app.router.add_static('/', WEB_DIR, show_index=False)`; `app.router.add_get('/ws', ws_server.make_handler(backend))`; `app.router.add_get('/api/health', health_handler)`.
- `async def health_handler(request) -> web.Response` — returns `{"status": "ok", "version": 1}` as JSON; useful for a quick manual `curl` check that the server is actually reachable, independent of WS.

### `server/ws_server.py`
- `make_handler(backend) -> Callable` — returns a closure so the aiohttp route can be registered without global state.
- `async def websocket_handler(request, backend) -> web.WebSocketResponse` — accepts the upgrade; logs `request.remote`; `try/finally` around the receive loop so `backend.force_release_all()` always fires on close/error (the disconnect-safety requirement — Wi-Fi hiccup or the iPad screen locking mid-drag must never leave a Mac mouse button stuck down); per-message `try/except (KeyError, json.JSONDecodeError, TypeError)` so one malformed message logs a warning and continues instead of killing the whole connection.
- `DISPATCH_TABLE: dict[str, Callable[[InputBackend, dict], None]]` — one entry per protocol message `type` (see Protocol section), each a small function that pulls fields out of the payload dict and calls the matching `InputBackend` method. `"hello"` is handled specially: replies immediately with `hello_ack` containing `backend.screen_size()`.

### `server/input/backend.py`
- `class InputBackend(Protocol)` (from `typing`) — declares the structural interface: `move_relative(dx, dy)`, `click()`, `right_click()`, `drag_start(fingers)`, `drag_move(dx, dy)`, `drag_end()`, `scroll(dx, dy, phase)`, `zoom(scale, phase)`, `swipe(fingers, direction)`, `force_release_all()`, `screen_size() -> tuple[int,int]`.
- `class QuartzBackend` — the real implementation, thin pass-through to the functions in `mouse.py`/`scroll.py`/`zoom.py`/`keyboard.py` (kept as module-level functions there since Quartz calls are stateless aside from the drag flag; `QuartzBackend` just adapts them to the `InputBackend` shape expected by `ws_server.py`).
- `class RecordingBackend` — implements the same interface but only appends `(method_name, args)` to `self.calls`; used exclusively by `tests/test_ws_dispatch.py`.
- `preflight_accessibility() -> bool` — `from ApplicationServices import AXIsProcessTrustedWithOptions, kAXTrustedCheckOptionPrompt` (exact pyobjc import path to confirm during implementation — may live under `Quartz` instead depending on pyobjc version); calls `AXIsProcessTrustedWithOptions({kAXTrustedCheckOptionPrompt: True})`, which itself triggers the native "grant Accessibility access" system prompt on first run; if it returns `False`, prints the exact `sys.executable` path and points to System Settings → Privacy & Security → Accessibility (calling this out specifically matters because recreating the venv changes the binary path and silently revokes a previous grant).

### `server/input/mouse.py`
All functions use the `Quartz` module (pyobjc). Concrete symbols used: `CGEventCreateMouseEvent`, `CGEventCreate`, `CGEventGetLocation`, `CGEventSetIntegerValueField`, `CGEventPost`, `CGDisplayBounds`, `CGMainDisplayID`, `kCGHIDEventTap`, `kCGEventMouseMoved`, `kCGEventLeftMouseDown`, `kCGEventLeftMouseUp`, `kCGEventLeftMouseDragged`, `kCGEventRightMouseDown`, `kCGEventRightMouseUp`, `kCGMouseButtonLeft`, `kCGMouseButtonRight`, `kCGMouseEventDeltaX`, `kCGMouseEventDeltaY`.

- `_current_location() -> CGPoint` — `CGEventGetLocation(CGEventCreate(None))`.
- `_clamp_to_display(point) -> CGPoint` — clamps against `CGDisplayBounds(CGMainDisplayID())` so the cursor can't be driven off-screen by a fast swipe.
- `move_relative(dx: float, dy: float) -> None` — computes `new_point = clamp(current + (dx, dy))`; builds a `kCGEventMouseMoved` event at `new_point`; also sets `kCGMouseEventDeltaX/Y` fields (some apps/games read raw HID deltas instead of absolute position, since `CGEventCreateMouseEvent` itself only accepts an absolute point); `CGEventPost(kCGHIDEventTap, event)`.
- `click() -> None` — posts `kCGEventLeftMouseDown` then `kCGEventLeftMouseUp` at the current location, back-to-back.
- `right_click() -> None` — same pattern with `kCGEventRightMouseDown/Up` and `kCGMouseButtonRight`.
- `drag_start() -> None` — posts `kCGEventLeftMouseDown`; sets module-level `_dragging = True`.
- `drag_move(dx, dy) -> None` — updates location like `move_relative` but posts `kCGEventLeftMouseDragged` (must be the `*Dragged` type, not `MouseMoved`, while a button is held — otherwise window/selection dragging doesn't track).
- `drag_end() -> None` — posts `kCGEventLeftMouseUp`; clears `_dragging`.
- `force_release_all() -> None` — if `_dragging` is still `True` (disconnect mid-drag), posts a `LeftMouseUp` at the current location and resets state; idempotent/safe to call even when nothing is dragging.
- `screen_size() -> tuple[int, int]` — reads `CGDisplayBounds(CGMainDisplayID())` width/height, used for the `hello_ack` reply (informational only in v1, no absolute-position mapping mode).

### `server/input/scroll.py`
- `scroll(dx: float, dy: float, phase: str = "changed") -> None` — `Quartz.CGEventCreateScrollWheelEvent2(None, kCGScrollEventUnitPixel, wheelCount=2, wheel1, wheel2, wheel3=0)`. Quartz's axis order is `wheel1=vertical, wheel2=horizontal`; apply `config.INVERT_SCROLL` as a sign flip before building the event; pixel units chosen over line units for a smooth trackpad-like feel rather than chunky mouse-wheel steps. `phase` accepted now for forward compatibility but unused in v1 (Phase 3 stretch: set `kCGScrollWheelEventScrollPhase`/`kCGScrollWheelEventMomentumPhase` fields for genuine inertial coasting once the client sends a `phase` sequence).

### `server/input/zoom.py`
- `apply(scale: float, phase: str = "changed") -> None` — pinch-zoom has **no public CGEvent API** (true magnify gestures are private `MultitouchSupport.framework`/`NSEventTypeMagnify` events with no public `CGEventCreateMagnifyEvent`). Fallback: convert the scale delta into a synthetic vertical scroll (`dy = (scale - 1.0) * config.ZOOM_SCROLL_GAIN`), build the scroll event exactly as in `scroll.py`, then `CGEventSetFlags(event, kCGEventFlagMaskCommand)` before posting — Safari/Preview/Photos/Accessibility Zoom already treat Cmd+scroll as a documented zoom gesture. Known limitation to document in README: not universal (e.g. Finder icon-size pinch won't respond); a private-API route via reverse-engineered `MultitouchSupport.framework` exists (used by tools like BetterTouchTool) but is out of scope.

### `server/input/keyboard.py`
- `KEYCODE_MODIFIER_FLAGS = {"control": Quartz.kCGEventFlagMaskControl, "command": Quartz.kCGEventFlagMaskCommand}` lookup.
- `send_shortcut(keycode: int, modifier: str | None = None) -> None` — `CGEventCreateKeyboardEvent(None, keycode, True)`, optionally `CGEventSetFlags(event, KEYCODE_MODIFIER_FLAGS[modifier])`, post, then post the matching key-up (`keydown=False`) event.
- `swipe(fingers: int, direction: str) -> None` — looks up `config.SWIPE_KEYCODE_MAP[fingers][direction]` and calls `send_shortcut(*mapping)`. 3/4-finger swipes have no public CGEvent path either (same private multitouch-event limitation as pinch), so this keyboard-shortcut substitution is the documented fallback for Mission Control (Control+Up), App Exposé (Control+Down), and Spaces switching (Control+Left/Right).

### `server/discovery.py`
- `get_lan_ip() -> str` — UDP-connect-to-`8.8.8.8` trick (`socket.socket(AF_INET, SOCK_DGRAM); s.connect(("8.8.8.8", 80)); s.getsockname()[0]`) — more reliable than `socket.gethostbyname(socket.gethostname())`, which can return the wrong interface on multi-homed Macs.
- `get_hostname_url(port: int) -> str` — `f"http://{socket.gethostname().split('.')[0]}.local:{port}"`; relies on macOS's built-in `mDNSResponder` auto-registering `<hostname>.local`, which resolves from any browser (including iPad Safari or the wrapper's WKWebView) via the OS DNS resolver — no custom mDNS browsing code needed or even possible from a browser.
- `class ZeroconfAdvertiser` — wraps `zeroconf.asyncio.AsyncZeroconf` (async variant, so registration doesn't block the aiohttp event loop) + `zeroconf.ServiceInfo(type_=config.ZEROCONF_TYPE, name=f"{config.SERVICE_NAME}.{config.ZEROCONF_TYPE}", ...)`; `async def start()` / `async def stop()`. Mainly future-proofing for a possible later native macOS-side companion/menu-bar app that could browse it via `NSNetServiceBrowser`; not load-bearing for the current Safari/WKWebView UX.
- `print_connection_info(port: int) -> None` — prints the hostname URL, the LAN-IP URL (fallback for networks that block multicast/mDNS reflection), and an ASCII QR code of the hostname URL via `qrcode.QRCode(...); qr.print_ascii(invert=True)` (no PIL/image dependency needed for terminal ASCII output) — this QR scan is the actual load-bearing zero-typing pairing UX given there's no native app on the browsing side.

### `docs/PROTOCOL.md`
Canonical schema (mirrors what's implemented in `web/js/protocol.js` and `server/ws_server.py`). Envelope: `{v, seq, t, type, ...payload}` where `v` is protocol version, `seq` a monotonic per-connection counter (drop/reorder detection while debugging), `t` a client `performance.now()` timestamp (latency measurement).

| type | payload | Mac action |
|---|---|---|
| `hello` | `{client:"web"}` | reply `hello_ack` `{serverVersion, macScreen:{width,height}}` |
| `move` | `{dx, dy}` | `mouse.move_relative(dx, dy)` |
| `click` | `{button:"left"}` | `mouse.click()` |
| `right_click` | `{}` | `mouse.right_click()` |
| `drag_start` | `{fingers:1\|3}` | `mouse.drag_start()` |
| `drag_move` | `{dx, dy, fingers}` | `mouse.drag_move(dx, dy)` |
| `drag_end` | `{fingers}` | `mouse.drag_end()` |
| `scroll` | `{dx, dy, phase}` | `scroll.scroll(dx, dy, phase)` |
| `zoom` | `{scale, phase}` | `zoom.apply(scale, phase)` |
| `swipe3` / `swipe4` | `{direction}` | `keyboard.swipe(3\|4, direction)` |

`fingers` is a discriminator field on `drag_*` rather than separate type names (`drag3_start`, etc.) because Mac-side handling is identical regardless of finger count.

---

## Component 2: Web Client (`web/`)

Plain ES modules (`<script type="module">`), no bundler/npm — Safari on iPadOS fully supports native ES module imports, so this keeps the whole project single-runtime (Python) aside from the browser itself.

### `web/index.html`
Full-viewport `<div id="surface">` that captures all touch input; `<meta name="viewport" content="width=device-width, viewport-fit=cover, user-scalable=no">`; a small status bar `<div id="status">` (colored dot: red=disconnected, yellow=connecting, green=connected) built by `main.js`; script tag `<script type="module" src="js/main.js"></script>` (module imports pull in the rest).

### `web/css/style.css`
Full-bleed dark background; `#surface { touch-action: none; -webkit-user-select: none; -webkit-touch-callout: none; overscroll-behavior: none; }` to suppress iOS's native pull-to-refresh/page-zoom/text-selection gestures that would otherwise fight with our own touch handling; status dot styling.

### `web/js/config.js`
```js
export const CONFIG = {
  WS_PATH: "/ws",
  TAP_MAX_DURATION_MS: 200, TAP_MAX_MOVEMENT_PX: 8,
  MOVE_THRESHOLD_PX: 4, DRAG_ARM_WINDOW_MS: 300,
  SCROLL_THRESHOLD_PX: 6, PINCH_THRESHOLD_PX: 10,
  SWIPE_MAX_DURATION_MS: 400, SWIPE_MIN_DISTANCE_PX: 60,
  SENSITIVITY: 1.5, ACCEL_DIVISOR: 40, ACCEL_MAX: 2.0,
  INVERT_SCROLL: false, DEBUG_SEND_RAW_TOUCHES: false,
  RECONNECT_BASE_MS: 500, RECONNECT_MAX_MS: 5000,
};
```

### `web/js/protocol.js`
`let seq = 0;` internal counter. `makeMessage(type, payload = {}) -> object` builds `{v:1, seq: seq++, t: performance.now(), type, ...payload}`. Typed builder helpers used by `main.js`/`gesture-recognizer.js` call sites: `helloMsg()`, `moveMsg(dx,dy)`, `clickMsg()`, `rightClickMsg()`, `dragStartMsg(fingers)`, `dragMoveMsg(dx,dy,fingers)`, `dragEndMsg(fingers)`, `scrollMsg(dx,dy,phase)`, `zoomMsg(scale,phase)`, `swipeMsg(fingers,direction)`.

### `web/js/touch-tracker.js`
`class TouchTracker`:
- `constructor(element)` — attaches `touchstart/touchmove/touchend/touchcancel` with `{passive: false}` (required so `preventDefault()` can actually block Safari's native scroll/zoom/callout).
- Maintains `Map<identifier, {x, y, startX, startY, startT}>`.
- `onChange(callback)` — registers `callback(activeTouches: Array<{id,x,y,startX,startY,startT}>, eventType: "start"|"move"|"end"|"cancel")`; keeps the recognizer decoupled from the raw DOM `Touch`/`TouchEvent` API.
- Private `_handleStart/_handleMove/_handleEnd(e)` update the map and call `preventDefault()` + fire `onChange`.

### `web/js/gesture-recognizer.js`
`class GestureRecognizer`:
- `constructor(onGesture: (type, payload) => void, onHaptic: (kind, style) => void)` — `onGesture` emits classified events up to `main.js` (which serializes via `protocol.js` and sends over WS); `onHaptic` fires local tactile feedback immediately (no WS round-trip — haptic response should feel instant, tied to local JS classification, not to a Mac ACK).
- Internal `this.state` enum: `IDLE, ONE_DOWN, MOVING, TAP_ARMED, DRAGGING, TWO_DOWN, SCROLLING, ZOOMING, THREE_DOWN, SWIPE_CANDIDATE, THREE_DRAG, FOUR_DOWN`.
- `handleTouchesChanged(touches, eventType)` — dispatches by `touches.length` to `_handleOneFinger/_handleTwoFinger/_handleThreeFinger/_handleFourFinger`. A session runs from `touches.size` 0→1 until it returns to 0; once a gesture type is classified it's **locked** for the session (finger-count decreasing mid-session ends the gesture rather than reinterpreting the remaining fingers — prevents bleed, e.g. lifting one of two scroll fingers must not suddenly pan the cursor with the remaining one).
- Helpers: `_centroid(touches)`, `_distance(p1, p2)`, timers via `setTimeout` for the tap-to-drag arm window and swipe duration window.
- Gesture logic (see full state-machine description below) fires `onHaptic("impact", "light")` on confirmed tap, `("impact","medium")` on right-click/swipe, `("selection")` on drag start, `("impact","light")` on drag end/drop.

### `web/js/haptics.js`
```js
const isNative = () =>
  !!(window.webkit?.messageHandlers?.haptics);

export function impact(style = "light") {
  if (isNative()) window.webkit.messageHandlers.haptics.postMessage({ type: "impact", style });
}
export function selection() {
  if (isNative()) window.webkit.messageHandlers.haptics.postMessage({ type: "selection" });
}
export function notification(style) {
  if (isNative()) window.webkit.messageHandlers.haptics.postMessage({ type: "notification", style });
}
export function prepare() {
  if (isNative()) window.webkit.messageHandlers.haptics.postMessage({ type: "prepare" });
}
```
Pure progressive enhancement: in plain Safari, `window.webkit.messageHandlers` is undefined, so every call is a silent no-op — the exact same JS runs in both the wrapper and a plain browser tab.

### `web/js/main.js`
- Opens `new WebSocket(location.origin.replace(/^http/, "ws") + CONFIG.WS_PATH)`.
- `ws.onopen` — send `helloMsg()`, update status dot to green, `haptics.notification("success")`.
- `ws.onclose`/`ws.onerror` — status dot to red, `haptics.notification("error")`, schedule reconnect with exponential backoff (`RECONNECT_BASE_MS` doubling, capped at `RECONNECT_MAX_MS`).
- `ws.onmessage` — handles `hello_ack` (logs server screen size, currently informational only).
- Instantiates `TouchTracker` on the `#surface` element and `GestureRecognizer`, wiring `recognizer` output to `ws.send(JSON.stringify(protocolBuilder(type, payload)))` and `haptics.*` calls per the trigger points above.

---

## Component 3: iOS Native Wrapper (`ios-app/`) — haptics only

A deliberately minimal SwiftUI + WKWebView shell. Its **only** job is to load the same web UI and bridge haptic calls to real Taptic Engine feedback; it contains no gesture logic, no networking beyond loading a URL — all of that stays in `web/js/`.

- **`IpadtrackapdApp.swift`** — `@main struct IpadtrackapdApp: App { var body: some Scene { WindowGroup { ContentView() } } }`.
- **`ContentView.swift`** — holds `@AppStorage("serverURL") var serverURL: String = ""`; on first launch (empty string) attempts the default `http://<hostname>.local:8765` guess or shows `SettingsView` to let the user paste the URL printed by the Mac server (fallback if `.local` resolution or QR scanning didn't work); hosts `WebViewContainer(url: serverURL)` full-screen, with a small gear icon to reopen `SettingsView`.
- **`WebViewContainer.swift`** — `UIViewRepresentable` wrapping `WKWebView`. `makeUIView`: builds a `WKWebViewConfiguration`, does `configuration.userContentController.add(context.coordinator, name: "haptics")`, loads `URLRequest(url:)` for the stored server URL. `Coordinator` (the `WKScriptMessageHandler`) is created in `makeCoordinator()` and holds the `HapticsBridge`.
- **`HapticsBridge.swift`** — `class HapticsBridge: NSObject, WKScriptMessageHandler`. `userContentController(_:didReceive:)` reads `message.body` as `[String: Any]`, switches on `body["type"]`:
  - `"impact"` → maps `body["style"]` string (`"light"/"medium"/"heavy"/"rigid"/"soft"`) to `UIImpactFeedbackGenerator.FeedbackStyle`, `UIImpactFeedbackGenerator(style:).impactOccurred()`.
  - `"selection"` → `UISelectionFeedbackGenerator().selectionChanged()`.
  - `"notification"` → maps `"success"/"warning"/"error"` to `UINotificationFeedbackGenerator.FeedbackType`, `.notificationOccurred(type)`.
  - `"prepare"` → pre-warms a generator (`.prepare()`) ahead of an anticipated gesture (fired on `touchstart` in the recognizer) to minimize first-hit latency — a documented iOS haptics best practice; the prepared generator is released/idle-timed out after ~2s of inactivity so Taptic Engine readiness isn't held indefinitely (battery).
- **`SettingsView.swift`** — a `TextField` bound to the `@AppStorage` server URL plus a "Save & Reload" button; exists because `.local` resolution occasionally fails on some routers/VPNs, giving the user a manual override that persists across launches.
- **`Info.plist`** — two required entries since this loads plain `http://` on the local network:
  - `NSAppTransportSecurity` → `NSExceptionDomains` → `"local"` → `NSExceptionAllowsInsecureHTTPLoads: true, NSIncludesSubdomains: true` (ATS blocks plain HTTP by default; this scopes the exception narrowly to `.local` rather than disabling ATS globally).
  - `NSLocalNetworkUsageDescription` — a user-facing string (e.g. "Used to connect to the Ipadtrackapd server running on your Mac"), required since iOS 14 for any local-network connection, including WKWebView loads to `.local`/LAN addresses; without it the app is silently blocked from connecting.

### `docs/HAPTICS.md`
Documents the bridge message schema (separate from `PROTOCOL.md` since it's local JS↔native, never sent over the WebSocket):
```
{ type: "impact", style: "light"|"medium"|"heavy"|"rigid"|"soft" }
{ type: "selection" }
{ type: "notification", style: "success"|"warning"|"error" }
{ type: "prepare" }
```

### Installation notes (for README)
Open `ios-app/Ipadtrackapd.xcodeproj` in Xcode; set the Signing Team to a personal Apple ID (free tier works); connect the iPad via cable once to trust the Mac; select the iPad as the run destination; Run. With a free (non-paid) account the app must be re-run from Xcode roughly every 7 days as the ad-hoc signature expires; a $99/yr Apple Developer Program membership removes that limitation if it becomes annoying.

---

## Gesture State Machine — full detail

Thresholds live in `web/js/config.js` (listed above). Behavior per finger count:

- **1-finger:** touchdown → `ONE_DOWN`. If lifted within `TAP_MAX_DURATION_MS` and cumulative movement `< TAP_MAX_MOVEMENT_PX` → emit `click`, fire `onHaptic("impact","light")`, then arm a `DRAG_ARM_WINDOW_MS` timer (`TAP_ARMED`); a new touchdown inside that window that then *moves* (not lifts) → `drag_start(fingers:1)` + `onHaptic("selection")` → repeated `drag_move` → `drag_end` + `onHaptic("impact","light")` on lift (replicates macOS's own "tap to drag" trackpad convention). If movement exceeds `MOVE_THRESHOLD_PX` before a tap is confirmed → locks into plain relative `move` (`MOVING` state, no click/haptic on lift).
- **2-finger:** second touchdown within ~150ms of the first opens `TWO_DOWN`. Each frame compute both centroid delta (scroll signal) and inter-point distance delta (pinch signal); whichever crosses its threshold (`SCROLL_THRESHOLD_PX` / `PINCH_THRESHOLD_PX`) first **locks** the session as `SCROLLING` or `ZOOMING` for its remainder (prevents flip-flopping mid-gesture). If both fingers lift within tap thresholds without either crossing → `right_click` + `onHaptic("impact","medium")`.
- **3-finger:** third touchdown opens `THREE_DOWN`, tracking centroid position/velocity. Fast short-distance movement completing within `SWIPE_MAX_DURATION_MS` and past `SWIPE_MIN_DISTANCE_PX` in one dominant axis → `swipe3` fired once + `onHaptic("impact","medium")`, further movement in that session ignored. Slower/sustained movement instead → `drag_start(fingers:3)`/`drag_move`/`drag_end` (three-finger window drag, implemented directly via mouse down/dragged/up rather than depending on any macOS accessibility setting).
- **4-finger:** swipe-only classification (same timing/distance rule as 3-finger), mapped to the 4-finger entries in `SWIPE_KEYCODE_MAP` (Spaces switching); no 4-finger drag in v1.
- **Disconnect safety:** `main.js`'s `ws.onclose` does not need to do anything mouse-related client-side — the authoritative safety net is server-side: `ws_server.py`'s `finally` block always calls `backend.force_release_all()`, so a mid-drag Wi-Fi drop or iPad screen lock never leaves the Mac's mouse button stuck down regardless of what state the JS recognizer was in when the connection died.

---

## Dependencies

`requirements.txt`:
```
aiohttp>=3.9
pyobjc-framework-Quartz>=10.0
pyobjc-framework-ApplicationServices>=10.0
zeroconf>=0.131
qrcode>=7.4
```
`requirements-dev.txt`:
```
-r requirements.txt
pytest>=8.0
```
`ios-app/` needs **no external Swift packages** — WebKit, UIKit, and SwiftUI are all system frameworks; Xcode is the only tooling requirement.

`scripts/run.sh`:
```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m venv .venv 2>/dev/null || true
source .venv/bin/activate
pip install -q -r requirements.txt
python -m server.main "$@"
```

---

## Phased Build Order

1. **Phase 0 — Scaffolding & discovery proof:** delete `main.py`; create the directory structure above; minimal aiohttp app serving a static page + echo WS route; verify the URL loads (both in plain Safari and, once scaffolded, the wrapper) and shows a live "connected" indicator.
2. **Phase 1 — Core parity:** single-finger relative move, tap-to-click, two-finger scroll, end-to-end including the Accessibility preflight. The single most validating milestone — actually moves the real Mac cursor from the iPad.
3. **Phase 2 — Right-click, click-drag, 3-finger window drag.**
4. **Phase 3 — Pinch-zoom + multi-finger swipes + scroll polish** (documented public-API fallbacks, not true system gesture events).
5. **Phase 4 — Native wrapper + haptics:** build `ios-app/`, wire `HapticsBridge`, add `haptics.js` calls at the trigger points listed in the state machine section, test on-device (haptics cannot be tested in Simulator — requires a physical iPad).
6. Deferred to v2 (explicitly out of scope now): reconnect/backoff UI polish beyond basic exponential backoff, sensitivity slider persisted via `localStorage`, Mac-side menu bar app/login item.

---

## Verification

**Automated:** only the WS message-dispatch seam is meaningfully unit-testable. `tests/test_ws_dispatch.py` uses `RecordingBackend` to assert e.g. `{"type":"scroll","dx":5,"dy":-3}` calls `backend.scroll(5,-3,...)` with correct arguments — no real screen or Accessibility permission needed, safe for CI. Everything else (CGEvent posting, gesture feel, haptics) requires manual on-device verification:

- **Phase 0:** connected indicator lights up on load; `/api/health` returns `{"status":"ok"}` via `curl`.
- **Phase 1:** finger-drag moves the cursor smoothly with no drift/lag; tap in a TextEdit field focuses and clicks correctly; two-finger scroll direction is correct and `INVERT_SCROLL` flips it.
- **Phase 2:** two-finger tap opens a context menu; tap-hold-move drags a Finder icon / selects text in TextEdit; three-finger title-bar drag relocates a window.
- **Phase 3:** pinch in Safari/Preview zooms (Cmd+scroll fallback); three/four-finger swipes trigger Mission Control/Exposé/Spaces.
- **Phase 4 (haptics, physical iPad required — no Simulator support):** tap produces a light buzz; right-click/swipe produce a medium buzz; drag start/end feel distinct; confirm haptics are silent (no crash, no console error) when the same page is opened in plain mobile Safari instead of the wrapper — proves the progressive-enhancement fallback actually works.
- **Disconnect test:** start a drag, then lock the iPad screen mid-gesture; confirm `force_release_all()` fires on WS close and the Mac's mouse button isn't left stuck down.
- **Latency/feel:** screen-record the iPad touch and Mac cursor simultaneously (QuickTime "New Movie Recording" with iPad as camera source) to eyeball perceived lag; target roughly sub-80ms over LAN Wi-Fi — document that this doesn't match a real Bluetooth trackpad's ~10-20ms, since that's an inherent limitation of WS-over-Wi-Fi, not a bug to keep chasing.
- **Debug tooling:** Safari remote Web Inspector (Mac Safari → Develop → [iPad/wrapper] → index.html; requires iPad Settings → Safari → Advanced → Web Inspector, and Mac Safari → Settings → Advanced → Show Develop menu) for live `console.log` on the gesture state machine, works against both plain Safari tabs and the WKWebView in the wrapper; pair with server-side `--verbose` logging of every dispatched CGEvent call.
