import logging
import socket

from odoo import _
from odoo.addons.hw_drivers.interface import Interface

_logger = logging.getLogger(__name__)

socket_devices = {}

class SocketInterface(Interface):
    connection_type = 'socket'

    def get_devices(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('', 9000))
            sock.listen(1)
            dev, addr = sock.accept()
            if addr and addr[0] not in socket_devices:
                socket_devices[addr[0]] = type('', (), {'dev': dev})
            return socket_devices
        except OSError as e:
            _logger.error('Error in SocketInterface: %s', e.strerror)
