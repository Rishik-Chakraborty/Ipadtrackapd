import socket
import logging
from zeroconf import ServiceInfo
from zeroconf.asyncio import AsyncZeroconf
import qrcode
from server import config

logger = logging.getLogger(__name__)

def get_lan_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

def get_hostname_url(port: int) -> str:
    hostname = socket.gethostname().split('.')[0]
    return f"http://{hostname}.local:{port}"

class ZeroconfAdvertiser:
    def __init__(self, port: int):
        self.port = port
        self.aiozc = None
        hostname = socket.gethostname().split('.')[0] + ".local."
        
        self.info = ServiceInfo(
            type_=config.ZEROCONF_TYPE,
            name=f"{config.SERVICE_NAME}.{config.ZEROCONF_TYPE}",
            addresses=[socket.inet_aton(get_lan_ip())],
            port=self.port,
            server=hostname
        )
        
    async def start(self):
        self.aiozc = AsyncZeroconf()
        await self.aiozc.async_register_service(self.info)
        logger.info(f"Zeroconf registered: {self.info.name}")
        
    async def stop(self):
        if self.aiozc:
            await self.aiozc.async_unregister_service(self.info)
            await self.aiozc.async_close()
            logger.info("Zeroconf unregistered")

def print_connection_info(port: int) -> None:
    url = get_hostname_url(port)
    ip_url = f"http://{get_lan_ip()}:{port}"
    
    print("\n" + "="*50)
    print("Ipadtrackapd Server Running")
    print("="*50)
    print(f"Connect your iPad to:\n  {url}")
    print(f"Fallback (LAN IP):\n  {ip_url}\n")
    print("Scan this QR code with your iPad camera:")
    
    qr = qrcode.QRCode(border=2)
    qr.add_data(url)
    qr.make(fit=True)
    qr.print_ascii(invert=True)
    
    print("="*50 + "\n")
