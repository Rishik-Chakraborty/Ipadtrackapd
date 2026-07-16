import argparse
import asyncio
import logging
import signal
import sys
from aiohttp import web

from server import config
from server.input.backend import preflight_accessibility, QuartzBackend
from server.app import create_app
from server.discovery import ZeroconfAdvertiser, print_connection_info

def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ipadtrackapd Server")
    parser.add_argument("--port", type=int, default=config.PORT, help="Port to listen on")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument("--no-qr", action="store_true", help="Disable QR code printing")
    parser.add_argument("--no-mdns", action="store_true", help="Disable mDNS registration")
    return parser

async def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    
    log_level = logging.DEBUG if args.verbose else getattr(logging, config.LOG_LEVEL)
    logging.basicConfig(level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    
    preflight_accessibility()
    
    backend = QuartzBackend()
    app = create_app(backend)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, config.HTTP_HOST, args.port)
    await site.start()
    
    advertiser = None
    if not args.no_mdns:
        advertiser = ZeroconfAdvertiser(args.port)
        await advertiser.start()
        
    if not args.no_qr:
        print_connection_info(args.port)
    else:
        logging.info(f"Server listening on port {args.port}")
        
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()
    
    def shutdown_signal():
        logging.info("Received shutdown signal...")
        stop_event.set()
        
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, shutdown_signal)
        
    await stop_event.wait()
    
    logging.info("Shutting down...")
    backend.force_release_all()
    if advertiser:
        await advertiser.stop()
    await runner.cleanup()

def run() -> None:
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    run()
