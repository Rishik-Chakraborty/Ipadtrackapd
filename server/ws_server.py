import json
import logging
from aiohttp import web
from server.input.backend import InputBackend

logger = logging.getLogger(__name__)

DISPATCH_TABLE = {
    "hello": lambda b, p: None,  # handled specially
    "move": lambda b, p: b.move_relative(p.get("dx", 0), p.get("dy", 0)),
    "click": lambda b, p: b.click(),
    "right_click": lambda b, p: b.right_click(),
    "drag_start": lambda b, p: b.drag_start(p.get("fingers", 1)),
    "drag_move": lambda b, p: b.drag_move(p.get("dx", 0), p.get("dy", 0)),
    "drag_end": lambda b, p: b.drag_end(),
    "scroll": lambda b, p: b.scroll(p.get("dx", 0), p.get("dy", 0), p.get("phase", "changed")),
    "zoom": lambda b, p: b.zoom(p.get("scale", 1.0), p.get("phase", "changed")),
    "swipe3": lambda b, p: b.swipe(3, p.get("direction", "")),
    "swipe4": lambda b, p: b.swipe(4, p.get("direction", "")),
}

def make_handler(backend: InputBackend):
    async def websocket_handler(request: web.Request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        logger.info(f"WebSocket connection established from {request.remote}")
        
        try:
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    try:
                        payload = json.loads(msg.data)
                        msg_type = payload.get("type")
                        
                        if msg_type == "hello":
                            width, height = backend.screen_size()
                            await ws.send_json({
                                "type": "hello_ack",
                                "serverVersion": 1,
                                "macScreen": {"width": width, "height": height}
                            })
                            continue
                            
                        handler = DISPATCH_TABLE.get(msg_type)
                        if handler:
                            handler(backend, payload)
                        else:
                            logger.warning(f"Unknown message type: {msg_type}")
                            
                    except (KeyError, json.JSONDecodeError, TypeError) as e:
                        logger.warning(f"Malformed message received: {msg.data}, error: {e}")
                elif msg.type == web.WSMsgType.ERROR:
                    logger.error(f"WebSocket connection closed with exception {ws.exception()}")
        finally:
            logger.info("WebSocket connection closed")
            backend.force_release_all()
            
        return ws
        
    return websocket_handler
