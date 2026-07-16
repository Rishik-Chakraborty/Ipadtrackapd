import os
from aiohttp import web
from server import ws_server
from server.input.backend import InputBackend

WEB_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web"))

async def health_handler(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok", "version": 1})

async def index_handler(request: web.Request) -> web.Response:
    return web.FileResponse(os.path.join(WEB_DIR, "index.html"))

def create_app(backend: InputBackend) -> web.Application:
    app = web.Application()

    app.router.add_get('/api/health', health_handler)
    app.router.add_get('/ws', ws_server.make_handler(backend))

    # aiohttp's static handler doesn't auto-serve index.html for '/' (show_index=False
    # just disables directory listings, it 403s a bare directory request otherwise),
    # so the root route needs to be wired explicitly.
    if os.path.exists(WEB_DIR):
        app.router.add_get('/', index_handler)
        app.router.add_static('/', WEB_DIR, show_index=False)

    return app
