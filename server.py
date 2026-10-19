"""
Profile Pic Studio - local web app.

Run:   python server.py      (or double-click start.bat)
Then the browser opens http://127.0.0.1:8765

The server only removes the background (rembg, runs offline on this PC).
Colours, templates and layout are done live in the browser.
"""

import io
import json
import threading
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError
from rembg import new_session, remove

HOST, PORT = "127.0.0.1", 8765        # localhost only: nothing is reachable from other devices
MODEL = "birefnet-portrait"           # best for people incl. hair/shoes; first run downloads it once
MAX_SIDE = 1600                       # downscale big phone photos first: much faster, output is 1080px anyway
MAX_UPLOAD = 40 * 1024 * 1024         # 40 MB
STATIC = Path(__file__).parent / "static"

session = None
model_lock = threading.Lock()         # one removal at a time; the model is heavy


def cutout(data: bytes) -> bytes:
    """Photo bytes -> PNG bytes of the person only, cropped to the person."""
    with Image.open(io.BytesIO(data)) as img:
        img = ImageOps.exif_transpose(img).convert("RGB")  # respect phone rotation
    img.thumbnail((MAX_SIDE, MAX_SIDE))
    with model_lock:
        out = remove(img, session=session).convert("RGBA")
    bbox = out.getchannel("A").point(lambda a: 255 if a > 10 else 0).getbbox()
    if bbox is None:
        raise ValueError("No person found in this photo. Try a clearer photo.")
    buf = io.BytesIO()
    out.crop(bbox).save(buf, "PNG")
    return buf.getvalue()


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC), **kwargs)

    def do_POST(self):
        if self.path != "/api/cutout":
            return self._json(404, {"error": "Not found"})
        length = int(self.headers.get("Content-Length") or 0)
        if not 0 < length <= MAX_UPLOAD:
            return self._json(413, {"error": "Photo must be smaller than 40 MB."})
        try:
            png = cutout(self.rfile.read(length))
        except (UnidentifiedImageError, OSError):
            return self._json(400, {"error": "That file is not a photo we can read. Use JPG or PNG."})
        except ValueError as e:
            return self._json(422, {"error": str(e)})
        self.send_response(200)
        self.send_header("Content-Type", "image/png")
        self.send_header("Content-Length", str(len(png)))
        self.end_headers()
        self.wfile.write(png)

    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    global session
    print(f"Loading background-removal model ({MODEL})... first run downloads it once.")
    session = new_session(MODEL)
    url = f"http://{HOST}:{PORT}"
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Profile Pic Studio running at {url}  (Ctrl+C to stop)")
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
