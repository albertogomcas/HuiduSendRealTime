"""
Huidu HD-WF4 LED Controller Real-time Display Update.

This module provides functionality to send images to a Huidu HD-WF4 LED controller
using the "Real-time area" feature. The implementation is based on reverse-engineered
packet captures from HDSign software.

Tested on a 160x32 Full Color screen supporting 8 different colors.
"""

import asyncio
import random
from typing import Optional

import numpy as np

try:
    import cv2
except ImportError:
    cv2 = None  # type: ignore

from udp_socket import UDPSocket


# Display dimensions
DISPLAY_WIDTH = 160
DISPLAY_HEIGHT = 32


def calculate_checksum(packet: bytearray) -> int:
    """Calculate checksum for a packet.

    Args:
        packet: The packet data to calculate checksum for.

    Returns:
        The checksum value as an integer.
    """
    checksum = 0
    for byte in packet:
        checksum += byte
    return checksum


def mat_to_packed_image(mat: np.ndarray) -> bytearray:
    """Convert a BGR image matrix to packed monochrome format.

    The format packs 8 pixels per byte, with interleaved color channels:
    - 1 line of 160 pixels of blue (20 bytes)
    - 1 line of 160 pixels of red (20 bytes)
    - 1 line of 160 pixels of green (20 bytes)
    Total: 60 bytes per line, 1920 bytes for 32 lines.

    Args:
        mat: A numpy array of shape (32, 160, 3) in BGR format.

    Returns:
        Packed image data as bytearray.
    """
    height, width = mat.shape[:2]

    # Extract color channels
    b = np.zeros((width * height,), dtype=np.uint8)
    g = np.zeros((width * height,), dtype=np.uint8)
    r = np.zeros((width * height,), dtype=np.uint8)

    for i in range(width):
        for j in range(height):
            idx = i + j * width
            pixel = mat[j, i]
            b[idx] = pixel[0]
            g[idx] = pixel[1]
            r[idx] = pixel[2]

    # Pack into monochrome format: threshold > 170 becomes 1, else 0
    # 8 pixels packed per byte, with color order: blue, red, green per line
    img = bytearray((width // 8) * 3 * height)

    for i in range(width):
        for j in range(height):
            idx = i + j * width
            idx2 = (i // 8) + j * 60
            bitshift = 7 - (i % 8)

            if b[idx] > 170:
                img[idx2] |= 1 << bitshift
            if r[idx] > 170:
                img[idx2 + 20] |= 1 << bitshift
            if g[idx] > 170:
                img[idx2 + 40] |= 1 << bitshift

    return img


async def send_mat(mat: np.ndarray, controller_ip: str = "192.168.4.1",
                   server_ip: str = "192.168.4.2") -> None:
    """Send an image matrix to the Huidu LED controller.

    Args:
        mat: A numpy array of shape (32, 160, 3) in BGR format.
        controller_ip: IP address of the Huidu controller (default: 192.168.4.1).
        server_ip: IP address to bind the server socket to (default: 192.168.4.2).
    """
    img = mat_to_packed_image(mat)

    # Counter and random IDs for packet headers
    cnt = 0x45
    id1 = random.randint(0, 255)
    id2 = random.randint(0, 255)

    # Packet 1 - Initialization packet
    paquete1 = bytearray([
        0x48, 0x54, 0x0, 0x1b, 0x0, 0x4d, 0x18, 0x0, 0xff, 0x0, 0x86, 0xe2,
        0x71, 0x0, 0xd, 0x20, 0x0, 0x1, 0xc4, 0x3f, 0x0, 0x0, 0x1, 0x0, 0x0,
        0x0, 0x4a, 0x2f, 0xad, 0xee, 0x0, 0x2, 0x0, 0x1, 0x0, 0x0, 0x0, 0x0,
        0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
        0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
        0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x7, 0x3d, 0xaa
    ])

    paquete1[0x1a] = cnt
    cnt += 1
    paquete1[0x1c] = id1
    paquete1[0x1d] = id2

    cksum = calculate_checksum(paquete1[:-3])
    paquete1[-2] = cksum & 0xFF
    paquete1[-3] = (cksum >> 8) & 0xFF

    # Packet 2 - First data packet with header and image data
    paquete2 = bytearray([
        0x48, 0x54, 0x0, 0x1b, 0x4, 0xb, 0x19, 0x0, 0xff, 0x0, 0x86, 0xe2,
        0x71, 0x0, 0xd, 0x20, 0x0, 0x1, 0xc4, 0x3f, 0x0, 0x0, 0x1, 0x0, 0x0,
        0x0, 0x1e, 0x5, 0xd5, 0x20, 0x0, 0x0, 0x48, 0x41, 0x0, 0x19, 0x0, 0x0,
        0x0, 0x0, 0x0, 0xa0, 0x0, 0x20, 0x0, 0x1, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
        0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x1d, 0x0, 0x17, 0x39, 0x0, 0x0,
        0x0, 0x0, 0x0, 0x0, 0x0, 0x1e, 0xc9, 0x3, 0x0, 0x1, 0x0, 0x0, 0x0, 0x17,
        0x0, 0x0, 0x7, 0x80
    ] + [0xff] * 940 + [0xb9, 0xa6, 0xaa])

    paquete2[0x1a] = cnt
    cnt += 1
    paquete2[0x1c] = id1
    paquete2[0x1d] = id2

    # Image starts at 0x54, count 640 bytes from the image buffer
    buf = len(paquete2) - 3 - 0x54  # 940 bytes
    for i in range(buf):
        paquete2[0x54 + i] = img[i]

    cksum = calculate_checksum(paquete2[:-3])
    paquete2[-2] = cksum & 0xFF
    paquete2[-3] = (cksum >> 8) & 0xFF

    # Packet 3 - Second data packet with remaining image data
    paquete3 = bytearray([
        0x48, 0x54, 0x0, 0x1b, 0x3, 0xef, 0x19, 0x0, 0xff, 0x0, 0x86, 0xe2,
        0x71, 0x0, 0xd, 0x20, 0x0, 0x1, 0xc4, 0x3f, 0x0, 0x0, 0x1, 0x0, 0x0,
        0x0, 0x4c, 0x5, 0xad, 0xee, 0x0, 0x1
    ] + [0xff] * 980 + [0xcf, 0xed, 0xaa])

    paquete3[0x1a] = cnt
    cnt += 1
    paquete3[0x1c] = id1
    paquete3[0x1d] = id2

    buf2 = len(paquete3) - 3 - 0x20  # 980 bytes
    for i in range(buf2):
        paquete3[0x20 + i] = img[buf + i]

    cksum = calculate_checksum(paquete3[:-3])
    paquete3[-2] = cksum & 0xFF
    paquete3[-3] = (cksum >> 8) & 0xFF

    # Packet 4 - Finalization packet
    paquete4 = bytearray([
        0x48, 0x54, 0x0, 0x1b, 0x0, 0x21, 0x1a, 0x0, 0xff, 0x0, 0x86, 0xe2,
        0x71, 0x0, 0xd, 0x20, 0x0, 0x1, 0xc4, 0x3f, 0x0, 0x0, 0x1, 0x0, 0x0,
        0x0, 0x4d, 0x3, 0xad, 0xee, 0x6, 0xe7, 0xaa
    ])

    paquete4[0x1a] = cnt
    cnt += 1
    paquete4[0x1c] = id1
    paquete4[0x1d] = id2

    cksum = calculate_checksum(paquete4[:-3])
    paquete4[-2] = cksum & 0xFF
    paquete4[-3] = (cksum >> 8) & 0xFF

    # Create sockets
    server_socket = UDPSocket()
    server_socket.server(server_ip, 12345)

    client_socket = UDPSocket()
    client_socket.client(controller_ip, 6101)

    # Send packets with delays
    client_socket.send(bytes(paquete1))
    await asyncio.sleep(0.1)

    client_socket.send(bytes(paquete2))
    await asyncio.sleep(0.25)

    client_socket.send(bytes(paquete3))
    await asyncio.sleep(0.25)

    client_socket.send(bytes(paquete4))
    await asyncio.sleep(0.1)

    # Close server socket
    server_socket.close()


def create_text_image(text: str, width: int = DISPLAY_WIDTH,
                      height: int = DISPLAY_HEIGHT) -> Optional[np.ndarray]:
    """Create an image with text using OpenCV.

    Args:
        text: The text to draw.
        width: Image width (default: 160).
        height: Image height (default: 32).

    Returns:
        A numpy array in BGR format, or None if OpenCV is not available.
    """
    if cv2 is None:
        print("OpenCV (cv2) is not available. Install opencv-python to use this function.")
        return None

    # Create black canvas
    mat = np.zeros((height, width, 3), dtype=np.uint8)

    # Draw white text
    cv2.putText(mat, text, (0, 25), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

    return mat


async def main() -> None:
    """Main entry point."""
    # Create an image with text
    mat = create_text_image("Hola")

    if mat is not None:
        await send_mat(mat)


if __name__ == "__main__":
    asyncio.run(main())
