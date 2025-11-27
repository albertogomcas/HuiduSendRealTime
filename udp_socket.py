"""UDP Socket wrapper for server/client communication."""

import socket
import threading
from typing import Callable, Optional


class UDPSocket:
    """UDP Socket class for sending and receiving UDP packets."""

    BUF_SIZE = 16 * 1024

    def __init__(self) -> None:
        """Initialize the UDP socket."""
        self._socket: Optional[socket.socket] = None
        self._receiving = False
        self._recv_thread: Optional[threading.Thread] = None
        self._callback: Optional[Callable[[bytes, tuple], None]] = None

    def server(self, address: str, port: int) -> None:
        """Create a UDP server socket bound to the given address and port.

        Args:
            address: The IP address to bind to.
            port: The port number to bind to.
        """
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.bind((address, port))
        self._receive()

    def client(self, address: str, port: int) -> None:
        """Create a UDP client socket connected to the given address and port.

        Args:
            address: The IP address to connect to.
            port: The port number to connect to.
        """
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.connect((address, port))
        self._receive()

    def send(self, data: bytes) -> None:
        """Send data through the socket.

        Args:
            data: The bytes to send.
        """
        if self._socket is None:
            return
        try:
            bytes_sent = self._socket.send(data)
            print(f"SEND: {bytes_sent}, {len(data)} bytes")
        except OSError as e:
            print(f"SEND error: {e}")

    def send_text(self, text: str) -> None:
        """Send a text string through the socket.

        Args:
            text: The text to send.
        """
        data = text.encode("ascii")
        self.send(data)

    def _receive(self) -> None:
        """Start receiving data in a background thread."""
        if self._socket is None:
            return
        self._receiving = True
        self._recv_thread = threading.Thread(target=self._receive_loop, daemon=True)
        self._recv_thread.start()

    def _receive_loop(self) -> None:
        """Background loop for receiving UDP packets."""
        if self._socket is None:
            return
        while self._receiving:
            try:
                data, addr = self._socket.recvfrom(self.BUF_SIZE)
                print(f"RECV: {addr}: {len(data)}, {data.decode('ascii', errors='replace')}")
                if self._callback:
                    self._callback(data, addr)
            except OSError:
                break

    def close(self) -> None:
        """Close the socket and stop receiving."""
        self._receiving = False
        if self._socket:
            self._socket.close()
            self._socket = None
