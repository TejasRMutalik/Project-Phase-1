"""
fetch_sample.py
Downloads a royalty-free sample traffic clip for M0 dev/demo use.
Run from the backend/ directory:
    python scripts/fetch_sample.py
"""

import os
import sys
import ssl
import urllib.request

ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
OUTPUT_PATH = os.path.join(ASSETS_DIR, "sample_traffic.mp4")

# Working public-domain video sources (tried in order)
SOURCES = [
    # Wikimedia Commons — Big Buck Bunny (small clip, always available)
    "https://upload.wikimedia.org/wikipedia/commons/transcoded/c/c0/Big_Buck_Bunny_4K.webm/Big_Buck_Bunny_4K.webm.480p.vp9.webm",
    # Internet Archive — traffic footage
    "https://ia800209.us.archive.org/13/items/SampleVideo1280x7205mb/SampleVideo_1280x720_5mb.mp4",
    # GitHub raw sample
    "https://github.com/intel-iot-devkit/sample-videos/raw/master/car-detection.mp4",
]

def download(url: str, dest: str, no_ssl: bool = False) -> bool:
    print(f"  Trying: {url}")
    try:
        def progress(block_num, block_size, total_size):
            downloaded = block_num * block_size
            if total_size > 0:
                pct = min(100, downloaded * 100 // total_size)
                print(f"\r  Downloading... {pct}%", end="", flush=True)

        if no_ssl:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx))
            urllib.request.install_opener(opener)

        urllib.request.urlretrieve(url, dest, reporthook=progress)
        print()
        return True
    except Exception as e:
        print(f"\n  Failed: {e}")
        if os.path.exists(dest):
            os.remove(dest)
        return False


def main():
    os.makedirs(ASSETS_DIR, exist_ok=True)

    if os.path.exists(OUTPUT_PATH):
        size_mb = os.path.getsize(OUTPUT_PATH) / (1024 * 1024)
        print(f"[OK] Sample clip already exists ({size_mb:.1f} MB): {OUTPUT_PATH}")
        return

    print("[M0] Downloading sample traffic clip...")
    for i, url in enumerate(SOURCES):
        # Try without SSL bypass first, then with on retry
        if download(url, OUTPUT_PATH, no_ssl=(i > 0)):
            size_mb = os.path.getsize(OUTPUT_PATH) / (1024 * 1024)
            print(f"[OK] Saved to: {OUTPUT_PATH} ({size_mb:.1f} MB)")
            return

    print("[ERROR] All download sources failed.")
    print("        Manually place any .mp4 traffic video at:")
    print(f"        {OUTPUT_PATH}")
    sys.exit(1)


if __name__ == "__main__":
    main()
