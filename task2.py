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
    return bytes(out)

def frame_payload(type, payload_bytes):
    magic = "STEG" # 4 bytes
    tbyte = 0x00 if type == "text" else 0x01 # 1 byte
    # length = payload_bytes.length as 4-byte big-endian
    length = len(payload_bytes).to_bytes(4, 'big') # 4 bytes
    return bytes(magic, 'utf-8') + bytes([tbyte]) + length + payload_bytes # 9-byte header + payload

def extract(stego_path, password):
    # arr = stego_image as (H, W, 3) array 
    arr = np.array(Image.open(stego_path).convert('RGB'))

    # print(f"Extracting from {stego_path} with password '{password}'")
    # print(f"Image dimensions: {arr.shape[0]}x{arr.shape[1]}, channels: {arr.shape[2]}")

    # print(arr)
    
    H, W, C = arr.shape
    total = H * W * 3
    
    # perm = permutation of [0..total-1] seeded by seed_from_password(password)
    perm = np.random.default_rng(seed_from_password(password)).permutation(total)
    bits = []
    header_seen = None

    # print(perm)
    
    for i in range(total):
        channel_pos = perm[i]
        pixel = channel_pos//3
        ch = channel_pos%3
        y = pixel // W
        x = pixel % W
        # print(f"Extracting bit from pixel ({y}, {x}), channel {ch}, value: {arr[y,x,ch]}")
        bits.append(arr[y,x,ch] & 1)

        if len(bits) == 72: # first 9 bytes = header
            header = bits_to_bytes(bits)

            if header[0:4] != b'STEG':
                print("STEG check failed: wrong password or not a stego image")
                return (None, None) # wrong password
            
            type = "text" if header[4] == 0 else "image"

            # length = int.to_bytes(header[5:9], 'big')
            length = int.from_bytes(header[5:9], 'big')
            total_bits_needed = (9 + length) * 8
            header_seen = True
            
        if header_seen and len(bits) >= total_bits_needed: 
            break
        
    payload_bytes = bits_to_bytes(bits[72 : 72 + length*8])
    # return ("text", payload.decode('utf-8')) or ("image", payload)
    if type == "text":
        return ("text", payload_bytes.decode('utf-8'))
    else:
        return ("image", payload_bytes)


# Recover and print the text from stego_text.png (expect "This is a secret").
print(extract("stego_text.png", "secret")[1])

# Recover the image from stego_laptop.png and display it (expect the laptop).
# extract("stego_laptop.png", "secret")
img_type, img_bytes = extract("stego_laptop.png", "secret")
if img_type == "image":
    # load the image from bytes and display it
    img = Image.open(BytesIO(img_bytes))
    img.show()

    # save the image to a file
    img.save("recovered_laptop.png", format="PNG")

# Run the extractor on stego_text.png with a wrong password and show that the STEG check fails and it reports no payload, rather than returning garbage.
print("\nWrong Password Test:")
print(extract("stego_text.png", "wrong_password")[1])