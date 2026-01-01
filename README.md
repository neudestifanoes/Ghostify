#Ghostify - Temporal Video Compression with Ghost Trails

Compress hours of traffic footage into seconds while preserving **all movement** and **temporal information** through color-coded ghost trails.

##Demo

**Original Video:** [Roundabout Traffic from Pexels](https://www.pexels.com/download/video/17870296/)
- Duration: 34 seconds
- Contains: Its a video of multiple cars passing through a roundabout

### Results Comparison

| Type | Screenshot | Description | Pros | Cons |
|------|------------|-------------|------|------|
| **[Original](https://www.pexels.com/download/video/17870296/)** | ![Original](examples/original_video_screenshot.png) | Standard 34-second traffic video | Full detail, natural colors | Long duration, hard to see patterns |
| **[Grayscale Ghost](https://youtu.be/-chbD_C2iws)** | ![Grayscale](examples/grayscale_ghost.png) | Clean black & white base layer | Neutral base, clear structure | No temporal information |
| **[Solid Ghost (Darken)](https://youtu.be/JGCdkc90-qQ)** | ![Solid](examples/solid_ghost_darken.png) | All segments darkened together | Shows all movement clearly | Dark/green tint, no temporal info |
| **[RGB Temporal](https://youtu.be/sZcRzFHI17s)** | ![RGB](examples/rgb_temporal.png) | Color-coded by time zones | Clear temporal separation | Too faint/transparent on its own |
| **[Hybrid Final](https://youtu.be/FLx7Rf3aGYs)** | ![Hybrid](examples/hybrid_final.png) | Grayscale + RGB overlay | **Best: Clear + Colorful + Temporal** | Requires two-step process |

---

## How It Works

### Color Coding System
-  **RED** = Cars from first 11 seconds (early)
-  **GREEN** = Cars from middle 11 seconds (middle)  
-  **BLUE** = Cars from last 11 seconds (late)

**Key Insight:** Static backgrounds appear in all time segments, so RED + GREEN + BLUE = natural color. Moving objects only appear in specific time windows, retaining their temporal color.

### Technical Process

```
Original Video (34s)
    ↓
[1] Analyze with PyAV → Extract I-frames (keyframes)
    ↓
[2] Split at I-frames → 12 segments of 3 seconds each
    ↓
[3a] Create Grayscale Ghost → Neutral base structure
[3b] Create RGB Temporal → Color-coded time zones
    ↓
[4] Overlay RGB on Grayscale → Final hybrid video (3s)
```

---

##  Installation

### Prerequisites
- Python 3.7+
- FFmpeg (must be installed and in PATH)

### Install FFmpeg

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg
```

**Windows:**
Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH

### Install Python Dependencies

```bash
pip install -r requirements.txt
```

---

##  Usage

### Step 1: Configure Paths

Edit the configuration section in `ghosting.py`:

```python
# Update these paths for your system
video_in = "/path/to/your/video.mp4"
csv_log = "video_analysis.csv"
output_folder = "/path/to/output"
seg_folder = "/path/to/segments"
ghost_out = "/path/to/rgb_ghost.mp4"
ghost_out2 = "/path/to/grayscale_ghost.mp4"
hybrid_out = "/path/to/final_hybrid.mp4"
```

### Step 2: Run the Complete Workflow

**Option A: Run all steps at once** (comment/uncomment as needed)

```python
# STEP 1: Analyze video (run once)
final_data = analyze_video(video_in)
if 'final_data' in locals(): 
    save_frame_report(final_data, output_folder)

# STEP 2: Split video (run once)
split_video_pro(video_in, csv_log, seg_folder)

# STEP 3: Create grayscale base
create_grayscale_ghost_video(seg_folder, csv_log, ghost_out2, 
                             num_segments=12, mode="lighten")

# STEP 4: Create RGB temporal overlay
create_temporal_ghost_video(seg_folder, csv_log, ghost_out, 
                            num_segments=12)

# STEP 5: Combine for final result
combine_ghost_videos(ghost_out2, ghost_out, hybrid_out, 
                    mode="overlay", opacity=0.6)
```

**Option B: Individual functions** for testing

```python
# Just create RGB temporal (fast, standalone)
create_temporal_ghost_video(seg_folder, csv_log, ghost_out, num_segments=12)

# Just create solid ghost (original method)
create_solid_ghost_video(seg_folder, csv_log, ghost_out2, mode="darken")
```

---

## Function Reference

### `analyze_video(file_path)`
Extracts frame information (I/P/B types, sizes, timestamps) using PyAV.

**Returns:** List of frame metadata dictionaries

---

### `split_video_pro(video_path, csv_path, output_dir)`
Splits video at I-frames (keyframes) into segments using FFmpeg.

**Parameters:**
- `video_path`: Input video file
- `csv_path`: CSV from `analyze_video()`
- `output_dir`: Where to save segments

---

### `create_grayscale_ghost_video(segments_dir, csv_path, output_file, num_segments=12, mode="lighten")`
Creates a clean black & white ghost video as base layer.

**Parameters:**
- `mode`: `"lighten"` (bright base) or `"darken"` (dark base)

**Best for:** Base layer for RGB overlay

---

### `create_solid_ghost_video(segments_dir, csv_path, output_file, mode="darken")`
Original ghost effect - overlays all segments with one blend mode.

**Parameters:**
- `mode`: `"darken"` (dark trails) or `"lighten"` (bright trails)

**Pros:** Simple, single-step process  
**Cons:** No temporal information, can have color tint

---

### `create_temporal_ghost_video(segments_dir, csv_path, output_file, num_segments=12)`
Creates RGB color-coded ghost video with temporal information.

**Time Zones:**
- Segments 0-3: RED
- Segments 4-7: GREEN  
- Segments 8-11: BLUE

**Pros:** Clear temporal separation  
**Cons:** Too faint to use alone (needs base layer)

---

### `combine_ghost_videos(solid_video_path, rgb_video_path, output_file, mode="overlay", opacity=0.6)`
Overlays RGB temporal video onto grayscale base.

**Parameters:**
- `mode`: Blend mode
  - `"overlay"` - Balanced (recommended)
  - `"hardlight"` - More intense colors
  - `"screen"` - Bright and vibrant
  - `"addition"` - Simple additive
- `opacity`: RGB layer transparency (0.0-1.0)

**Recommended settings:**
- `mode="overlay"`, `opacity=0.6` (balanced)
- `mode="hardlight"`, `opacity=0.7` (vibrant)

---

##  Best Practices

### Video Selection
 **Good for:**
- Traffic intersections
- Roundabouts
- Pedestrian crossings
- Wildlife trails
- Time-lapse of moving objects

 **Not ideal for:**
- Handheld/shaky footage
- Videos with camera movement
- Low frame rate videos

### Optimal Settings

**For bright, colorful results:**
```python
create_grayscale_ghost_video(..., mode="lighten")
combine_ghost_videos(..., mode="overlay", opacity=0.6)
```

**For dramatic, high-contrast:**
```python
create_grayscale_ghost_video(..., mode="lighten")
combine_ghost_videos(..., mode="hardlight", opacity=0.7)
```

---

##  Troubleshooting

### Issue: "FFmpeg not found"
**Solution:** Install FFmpeg and ensure it's in your system PATH

### Issue: RGB video is all one color
**Solution:** Check that your video has 12+ I-frames. Use `analyze_video()` to verify GOP structure.

### Issue: Background has color tint
**Solution:** 
- Use grayscale base instead of solid ghost
- Try `mode="overlay"` with lower `opacity` (0.4-0.6)

### Issue: Colors too faint
**Solution:** 
- Increase `opacity` parameter (0.7-0.9)
- Try `mode="hardlight"` for more intense colors

### Issue: Last segment errors
**Solution:** The code automatically pads the final short segment. Ensure `num_segments` matches your actual segment count.

---

##  Performance Notes

- **Analysis time:** ~30 seconds per minute of video
- **Splitting:** Very fast (copy operation, no re-encode)
- **Ghosting:** ~2-5 minutes depending on complexity
- **Memory usage:** Minimal (processes in streaming fashion)

---

##  Understanding the Code

### Why I-frames?
I-frames (keyframes) are complete images, while P/B frames store differences. Splitting at I-frames ensures:
- No visual artifacts
- Fast processing (no re-encoding)
- Clean segment boundaries

### Blend Modes Explained

| Mode | Effect | Best Use |
|------|--------|----------|
| `darken` | Keeps darkest pixels | Original ghost effect |
| `lighten` | Keeps brightest pixels | Bright base layer |
| `overlay` | Balanced contrast blend | RGB overlay (recommended) |
| `hardlight` | Strong contrast | Vibrant colors |
| `screen` | Additive brightening | Bright, washed effect |

### Color Channel Mixer

The RGB temporal effect uses FFmpeg's `colorchannelmixer`:
```
rr=1.0:rg=0:rb=0  → Keep only RED channel
gr=0:gg=1.0:gb=0  → Keep only GREEN channel
br=0:bg=0:bb=1.0  → Keep only BLUE channel
```

This isolates each color, ensuring temporal clarity.

---



