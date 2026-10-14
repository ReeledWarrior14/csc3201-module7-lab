from io import BytesIO

from Crypto.Hash import SHA256
from PIL import Image

import numpy as np

def seed_from_password(password):
    h = SHA256.new(password.encode('utf-8')).digest()
    # return first 8 bytes of h, interpreted as a big-endian integer
    return int.from_bytes(h[:8], 'big')
    
def capacity_bytes(height, width, channels=3):
    return (height * width * channels) // 8 # 1 bit per channel

def bytes_to_bits(data):
    bits = []
    # for each byte b in data:
    #     for i from 7 down to 0: # most-significant bit first
    #         append ((b >> i) AND 1) to bits
    for b in data:
        for i in range(7, -1, -1):
            bits.append((b >> i) & 1)
    return bits

def bits_to_bytes(bits):
    # pad bits with 0s until length is a multiple of 8
    while len(bits) % 8 != 0:
        bits.append(0)
    out = []
    for group in range(0, len(bits), 8):
        # assemble them into one byte (first bit = high bit)
        # append byte to out
        byte = 0
        for i in range(8):
            byte = (byte << 1) | bits[group + i]
        out.append(byte)
    return out

def frame_payload(type, payload_bytes):
    magic = "STEG" # 4 bytes
    tbyte = 0x00 if type == "text" else 0x01 # 1 byte
    # length = payload_bytes.length as 4-byte big-endian
    length = len(payload_bytes).to_bytes(4, 'big') # 4 bytes
    return bytes(magic, 'utf-8') + bytes([tbyte]) + length + payload_bytes # 9-byte header + payload
# password = 123
# rng = np.random.default_rng(seed_from_password(password))
# perm = rng.permutation(total_channels) # total_channels = H * W * 3


def embed(cover_path, out_path, type, payload_bytes, password):
    # image = load image as RGB
    image = Image.open(cover_path).convert('RGB')
    # arr = image as array of shape (H, W, 3)
    arr = np.array(image)

    # total_channels = H * W * 3
    H, W, C = arr.shape
    # print(f"Image dimensions: {H}x{W}, channels: {C}")
    total_channels = H * W * 3
    
    framed = frame_payload(type, payload_bytes)
    bits = bytes_to_bits(framed)

    # print(f"Payload size: {len(payload_bytes)} bytes, framed size: {len(framed)} bytes, bits to embed: {len(bits)} bits")
    # print(f"Image capacity: {capacity_bytes(H, W, C)} bytes, total channels: {total_channels}")

    # CAPACITY CHECK -- refuse rather than silently truncate
    if len(bits) > total_channels:
        # raise error "payload too large for this cover"
        raise ValueError("payload too large for this cover")
    
    # perm = permutation of [0 .. total_channels-1]
    # seeded by seed_from_password(password)
    # out = copy of arr
    perm = np.random.default_rng(seed_from_password(password)).permutation(total_channels)
    out = np.copy(arr)

    # print(perm)
    
    for i in range(0, len(bits) - 1):
        channel_pos = perm[i] # which channel to use
        pixel = channel_pos // 3 # map flat index -> pixel + channel
        ch = channel_pos % 3
        y = pixel // W
        x = pixel % W
        out[y,x,ch] = (out[y,x,ch] & 0xFE) | bits[i] # clear LSB, set it
    # save out as PNG (lossless) to out_path``
    out_image = Image.fromarray(out)
    out_image.save(out_path, format='PNG')

# stego_text.png -> hide the text "This is a secret" in apple_logo_cover.png.
embed("apple_logo_cover.png", "stego_text.png", "text", b"This is a secret", "123")


# stego_laptop.png -> hide laptop_secret.png in apple_logo_cover.png.
# (Re-encode the laptop image to PNG bytes in memory, then pass those bytes as the payload with type "image".)
# laptop_secret_image = Image.open("laptop_secret.png").convert('RGB')
# laptop_secret_bytes = laptop_secret_image.tobytes() # get raw bytes of the image
secret_image = Image.open("laptop_secret.png")

buffer = BytesIO()
secret_image.save(buffer, format="PNG")
payload_bytes = buffer.getvalue()

embed("apple_logo_cover.png", "stego_laptop.png", "image", payload_bytes, "123")

