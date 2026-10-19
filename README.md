# Profile Pic Studio

A small local web app that turns any photo of a person into a polished, square profile picture. Upload a photo, the background is removed automatically, then pick a colour template, tweak it, and download a 1080 × 1080 PNG.

Everything runs on your own computer. Photos are never uploaded to any external service.

## Features

- **Automatic background removal** using [rembg](https://github.com/danielgatis/rembg) with the `birefnet-portrait` model, which handles hair and fine edges well.
- **8 ready-made templates**: Ocean, Sunset, Forest, Royal, Gold, Clean, Candy, Mono.
- **Live customisation**: every change redraws the preview instantly.
  - Background colour, two-colour gradient circle, circle border colour
  - White (or any colour) outline around the person
  - Circle size and vertical position, circle border thickness
  - Person size, left/right position, outline thickness
  - Soft drop shadow on/off
  - Transparent background on/off (for use on your own backgrounds)
- **Fits round profile crops**: Facebook, Instagram and WhatsApp show profile pictures as a circle. The person is kept inside that circle, with the body clipped to the ring and the head free to pop out above it. A **Show round crop** toggle dims everything the platforms will hide (preview only, not in the download).
- **Download as PNG** at 1080 × 1080, a size that works for WhatsApp, LinkedIn, Instagram, X and most other platforms.
- **Background removal only**: the **Download background removed only** button saves just the person on a transparent background (`background-removed.png`), with no template or design. It is cropped to the person and at most 1600 px on the longest side.
- **Drag and drop** or click to upload. Phone photos are rotated correctly using their EXIF data.

## Requirements

- **Python 3.9 or newer** (developed on Python 3.11, 64-bit)
- **About 3 GB of free RAM** while the server is running. The background-removal model is large, and loading it fails with `bad allocation` if memory is short.
- **About 1 GB of disk space** for the model, which is downloaded once on first run.
- An internet connection **only for the first run**, to download the model. After that it works fully offline.

## Installation

```bash
git clone https://github.com/mridul82/profile-pic-studio.git
cd profile-pic-studio
pip install -r requirements.txt
```

`requirements.txt` installs:

| Package     | Purpose                                         |
|-------------|-------------------------------------------------|
| `rembg[cpu]`| Background removal (runs on CPU via ONNX Runtime) |
| `pillow`    | Reading, rotating, resizing and cropping images |

## Running

**Windows:** double-click `start.bat`.

**Any OS:**

```bash
python server.py
```

The first start prints `Loading background-removal model...` and downloads the model (~970 MB) into `~/.rembg/models/`. This can take a few minutes. Later starts only need to load it from disk.

When it is ready you will see:

```
Profile Pic Studio running at http://127.0.0.1:8765  (Ctrl+C to stop)
```

Your browser opens that address automatically. Press **Ctrl+C** in the terminal to stop the server.

## How to use

1. **Upload your photo.** Click the upload box or drag a photo onto it. Full-body or half-body photos with the person clearly visible work best. Processing takes from a few seconds up to about a minute, depending on your CPU.
2. **Choose a template.** Click any of the eight swatches to apply its colour set.
3. **Customise.** Adjust colours, sliders and checkboxes. The preview updates as you go.
4. **Download.** Click **Download PNG** to save `profile-picture.png`. Use **Change photo** to start over with a different photo while keeping your design settings.

## How it works

The work is split in two: the Python server does only the heavy AI step, and the browser does all the design work.

```
Browser (static/index.html)                 Python server (server.py)
───────────────────────────                 ─────────────────────────
1. You pick a photo
2. POST raw image bytes  ───────────────▶   3. Rotate per EXIF, shrink to max 1600 px
   to /api/cutout                           4. rembg removes the background
                                            5. Crop tightly around the person
6. Receive transparent PNG  ◀───────────    
7. Draw on a 1080×1080 canvas:
   background → border ring → gradient circle
   → outlined person → optional shadow
8. Redraw instantly on every setting change
9. Export the canvas as PNG
```

### Server (`server.py`)

- Built on Python's standard-library `http.server`, so there is no web framework to install.
- Serves the files in `static/` and exposes a single endpoint: **`POST /api/cutout`**.
  - **Request body:** the raw image file (JPG, PNG or anything Pillow can read).
  - **Success:** `200` with a PNG of the person on a transparent background, cropped to the person.
  - **Errors** (JSON `{"error": "..."}`):
    - `400`: the file is not a readable image
    - `413`: the file is empty or larger than 40 MB
    - `422`: no person was found in the photo
- Large photos are scaled down to 1600 px on the longest side before processing. This makes removal much faster, and the final picture is only 1080 px anyway.
- The model is loaded once at startup and shared. A lock lets only one photo be processed at a time, because the model uses a lot of memory.

### Frontend (`static/index.html`)

- A single HTML file with plain JavaScript and CSS. There is no build step and nothing is fetched from the internet.
- The outline around the person is made by stamping a solid-colour copy of the person's silhouette 48 times in a circle around it, then drawing the person on top.
- Because all compositing happens on an HTML canvas, changing a colour or slider never calls the server again.

## Configuration

Settings are constants at the top of `server.py`:

| Constant     | Default               | What it does |
|--------------|-----------------------|--------------|
| `HOST`       | `127.0.0.1`           | Address to listen on. Localhost only, so other devices cannot reach it. |
| `PORT`       | `8765`                | Port number. |
| `MODEL`      | `birefnet-portrait`   | rembg model name. |
| `MAX_SIDE`   | `1600`                | Photos are downscaled to this many pixels on the longest side before processing. |
| `MAX_UPLOAD` | `40 MB`               | Largest accepted upload. |

### Using a smaller model

If your computer has little RAM, change `MODEL` to a lighter model. Quality around hair is lower, but it loads with much less memory:

| Model               | Download size | Notes |
|---------------------|---------------|-------|
| `birefnet-portrait` | ~970 MB       | Default. Best edges for people. |
| `isnet-general-use` | ~180 MB       | Good general-purpose quality. |
| `u2net_human_seg`   | ~170 MB       | Trained for people, softer edges. |

## Project structure

```
profile-pic-studio/
├── server.py          # Local web server + background-removal endpoint
├── static/
│   └── index.html     # The whole user interface (HTML + CSS + JS)
├── requirements.txt   # Python dependencies
├── start.bat          # Windows launcher (double-click to run)
└── README.md
```

## Troubleshooting

**`bad allocation` or the server crashes while loading the model**
Not enough free memory. Close other programs or browser tabs and try again, or switch to a smaller model (see above). Also check that another copy of `server.py` is not still running in the background, for example one started from an older folder. It keeps the model in memory and holds the port.

**`OSError: [WinError 10048]` / "address already in use"**
Something is already using port 8765, usually another copy of this server. Stop it, or change `PORT` in `server.py`.

**"Can't reach the server. Is server.py still running?"**
The terminal running the server was closed or the server crashed. Start it again.

**"No person found in this photo"**
The model could not find a clear subject. Use a photo where the person is large in the frame and well lit.

**The first run is very slow**
It is downloading the ~970 MB model. This happens only once.

**Background removal takes a long time**
It runs on the CPU. Expect anywhere from a few seconds to about a minute per photo, depending on your machine.

## Privacy

- The server listens only on `127.0.0.1`, so it is reachable only from the same computer.
- Photos are processed in memory and are never saved to disk or sent anywhere.
- The only network access is the one-time model download on first run.
