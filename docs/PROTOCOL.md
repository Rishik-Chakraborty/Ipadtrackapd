# Ipadtrackapd Protocol

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
