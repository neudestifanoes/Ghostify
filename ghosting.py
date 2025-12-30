import av
from av.video.frame import PictureType
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import pandas as pd
import os
import subprocess


def analyze_video(file_path):
    """
    Uses PyAV to probe the video container and extract the type (I, P, B) 
    and compressed size of every frame.
    """
    try:
        container = av.open(file_path)
        results = []
        frame_count = 0

        for packet in container.demux(video=0):
            for frame in packet.decode():
                try:
                    ptype = PictureType(frame.pict_type).name
                except (ValueError, AttributeError):
                    ptype = "Unknown"

                results.append({
                    'index': frame_count,
                    'type': ptype,
                    'pts': frame.pts,
                    'size': packet.size 
                })
                
                if frame_count % 100 == 0:
                    print(f"Processed {frame_count} frames...")
                frame_count += 1

        container.close()
        return results
    except Exception as e:
        print(f"An error occurred during analysis: {e}")
        return []


def plot_frames(frame_data):
    """
    Visualizes the GOP (Group of Pictures) structure using Matplotlib.
    High red bars indicate I-frames (keyframes).
    """
    if not frame_data:
        print("No data to plot.")
        return

    indices = [f['index'] for f in frame_data]
    sizes = [f['size'] for f in frame_data]
    types = [f['type'] for f in frame_data]
    
    colors_map = {'I': 'red', 'P': 'blue', 'B': 'green', 'Unknown': 'gray'}
    frame_colors = [colors_map.get(t, 'gray') for t in types]

    plt.figure(figsize=(14, 7))
    plt.bar(indices, sizes, color=frame_colors, width=1.0)
    plt.xlabel('Frame Index')
    plt.ylabel('Compressed Size (Bytes)')
    plt.title('Video Frame Analysis: GOP Structure')
    
    legend_elements = [Line2D([0], [0], color='red', lw=4, label='I-Frame (Keyframe)'),
                       Line2D([0], [0], color='blue', lw=4, label='P-Frame (Predicted)'),
                       Line2D([0], [0], color='green', lw=4, label='B-Frame (Bi-dir)')]
    plt.legend(handles=legend_elements)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.show()


def save_frame_report(frame_data, destination_folder, filename="video_analysis.csv"):
    """
    Saves the analyzed frame data into a CSV for later use in splitting/blending.
    """
    df = pd.DataFrame(frame_data)
    df['size_kb'] = (df['size'] / 1024).round(2)
    full_path = os.path.join(destination_folder, filename)
    
    try:
        df.to_csv(full_path, index=False)
        print(f"--- SUCCESS: Report saved to {full_path} ---")
    except Exception as e:
        print(f"Failed to save file: {e}")


def split_video_pro(video_path, csv_path, output_dir):
    """
    Uses the FFmpeg 'segment' muxer to chop the video at every I-frame.
    'reset_timestamps 1' ensures every segment starts at 0.0s for the blending step.
    """
    df = pd.read_csv(csv_path)
    iframes = df[df['type'] == 'I']
    
    # Calculate split points based on the 90000 timebase
    split_points = [f"{pts/90000:.4f}" for pts in iframes['pts'] if pts > 0]
    times_string = ",".join(split_points)
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    output_pattern = os.path.join(output_dir, "segment_%03d.mp4")

    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-f", "segment", "-segment_times", times_string,
        "-reset_timestamps", "1", "-map", "0", "-c", "copy",
        output_pattern
    ]

    print("Running split at I-frames...")
    subprocess.run(cmd)
    print(f"Split complete. Files saved in: {output_dir}")


def create_grayscale_ghost_video(segments_dir, csv_path, output_file, num_segments=12, mode="lighten"):
    """
    Creates a clean grayscale ghost video as a base for RGB overlay.
    Converts to grayscale first, then blends for a neutral white/gray base.
    """
    df = pd.read_csv(csv_path)
    total_frames = len(df)
    last_iframe_idx = df[df['type'] == 'I']['index'].max()
    
    frames_in_last = total_frames - last_iframe_idx
    padding_needed = 90 - frames_in_last 
    
    input_args = []
    for i in range(num_segments):
        file_path = os.path.join(segments_dir, f"segment_{i:03d}.mp4")
        input_args.extend(["-i", file_path])

    # Build filter: convert each segment to grayscale, then blend
    filter_parts = []
    
    # Convert each segment to grayscale (except last, which needs padding)
    for i in range(num_segments - 1):
        filter_parts.append(f"[{i}:v]hue=s=0[v{i}_gray]")
    
    # Pad and grayscale the last segment
    filter_parts.append(f"[{num_segments-1}:v]tpad=stop={padding_needed}:stop_mode=clone,hue=s=0[v{num_segments-1}_gray]")
    
    # Blend all grayscale segments
    last_label = "[v0_gray]"
    for i in range(1, num_segments):
        next_label = f"[b{i}]" if i < num_segments - 1 else "[outv]"
        filter_parts.append(f"{last_label}[v{i}_gray]blend=all_mode={mode}{next_label}")
        last_label = next_label
    
    filter_complex = "; ".join(filter_parts)

    cmd = [
        "ffmpeg", "-y"
    ] + input_args + [
        "-filter_complex", filter_complex,
        "-map", "[outv]", "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
        output_file
    ]

    print(f"Generating Grayscale Ghost Base (Mode: {mode})...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"Success! Grayscale ghost video: {output_file}")
    else:
        print("FFmpeg Error:\n", result.stderr)


def create_temporal_ghost_video(segments_dir, csv_path, output_file, num_segments=12):
    """
    Creates a ghost video with temporal information encoded via RGB color zones:
    - Early segments (0-3): RED tint
    - Middle segments (4-7): GREEN tint
    - Late segments (8-11): BLUE tint
    
    Static background: R+G+B = natural color
    Moving objects: retain their zone color = temporal identification
    """
    df = pd.read_csv(csv_path)
    total_frames = len(df)
    last_iframe_idx = df[df['type'] == 'I']['index'].max()
    
    # Handle the short final segment by padding
    frames_in_last = total_frames - last_iframe_idx
    padding_needed = 90 - frames_in_last
    
    # Build input arguments
    input_args = []
    for i in range(num_segments):
        file_path = os.path.join(segments_dir, f"segment_{i:03d}.mp4")
        input_args.extend(["-i", file_path])
    
    # Build the complex filter with RGB temporal zones
    filter_parts = []
    
    # Pad the last segment first
    filter_parts.append(f"[{num_segments-1}:v]tpad=stop={padding_needed}:stop_mode=clone[v{num_segments-1}_padded]")
    
    # Determine which third each segment belongs to
    third_size = num_segments / 3
    
    # Apply color zone to each segment
    for i in range(num_segments):
        input_label = f"[v{i}_padded]" if i == num_segments-1 else f"[{i}:v]"
        output_label = f"[v{i}_processed]"
        
        # Determine color zone based on segment index
        if i < third_size:
            # Early: RED zone (keep red, reduce green and blue)
            color_filter = "colorchannelmixer=rr=1.0:rg=0:rb=0:gr=0:gg=0:gb=0:br=0:bg=0:bb=0"
            zone = "RED"
        elif i < 2 * third_size:
            # Middle: GREEN zone (keep green, reduce red and blue)
            color_filter = "colorchannelmixer=rr=0:rg=0:rb=0:gr=0:gg=1.0:gb=0:br=0:bg=0:bb=0"
            zone = "GREEN"
        else:
            # Late: BLUE zone (keep blue, reduce red and green)
            color_filter = "colorchannelmixer=rr=0:rg=0:rb=0:gr=0:gg=0:gb=0:br=0:bg=0:bb=1.0"
            zone = "BLUE"
        
        # Apply color zone
        filter_parts.append(f"{input_label}{color_filter}{output_label}")
        print(f"  Segment {i:02d}: {zone} zone")
    
    # Now blend all processed segments using lighten mode (better for RGB additive)
    # Start with first segment
    last_label = "[v0_processed]"
    
    for i in range(1, num_segments):
        next_label = f"[blend{i}]" if i < num_segments - 1 else "[outv]"
        filter_parts.append(
            f"{last_label}[v{i}_processed]blend=all_mode=lighten{next_label}"
        )
        last_label = next_label
    
    filter_complex = "; ".join(filter_parts)
    
    cmd = [
        "ffmpeg", "-y"
    ] + input_args + [
        "-filter_complex", filter_complex,
        "-map", "[outv]", "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
        output_file
    ]
    
    print(f"Generating RGB Temporal Ghost Video...")
    print(f"  - Early (segments 0-3): RED")
    print(f"  - Middle (segments 4-7): GREEN")
    print(f"  - Late (segments 8-11): BLUE")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"Success! RGB temporal ghost video: {output_file}")
    else:
        print("FFmpeg Error:\n", result.stderr)


def combine_ghost_videos(solid_video_path, rgb_video_path, output_file, mode="overlay", opacity=0.6):
    """
    Overlays the RGB Ghost video onto the Solid Ghost video.
    
    Blend mode options:
    - 'overlay': Balanced, natural color overlay (recommended)
    - 'hardlight': More intense, vibrant colors
    - 'screen': Bright and washed out effect
    - 'addition': Simple additive blending
    
    Opacity: Controls how strong the RGB colors appear (0.0 = invisible, 1.0 = full strength)
    """
    
    # Adjust the RGB opacity before blending for better control
    cmd = [
        "ffmpeg", "-y",
        "-i", solid_video_path,  # Input 0: The Structure (Grayscale/Solid)
        "-i", rgb_video_path,    # Input 1: The Color (RGB)
        "-filter_complex", 
        f"[1:v]format=yuva420p,colorchannelmixer=aa={opacity}[rgb_adjusted];"
        f"[0:v][rgb_adjusted]blend=all_mode={mode}[outv]",
        "-map", "[outv]", 
        "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
        output_file
    ]

    print(f"Generating Composite Hybrid (Mode: {mode}, Opacity: {opacity})...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"Success! Hybrid ghost video saved to: {output_file}")
    else:
        print("FFmpeg Error:\n", result.stderr)


# ============================================================================
# SETUP - Change these paths to match your files
# ============================================================================
video_in = "/Users/neudestifanoes/desktop/claude/thevideo.mp4"
csv_log = "video_analysis.csv"
output_folder = "/Users/neudestifanoes/desktop/claude"
seg_folder = "/Users/neudestifanoes/desktop/claude/segments_fixed"
ghost_out = "/Users/neudestifanoes/desktop/claude/rgb_ghost.mp4"
ghost_out2 = "/Users/neudestifanoes/desktop/claude/grayscale.mp4"
hybrid_out = "/Users/neudestifanoes/desktop/claude/final_hybrid.mp4"


# ============================================================================
# HOW TO USE - Uncomment the lines you need
# ============================================================================

# For running for first time? Run these lines once then comment them out:
#final_data = analyze_video(video_in)
#save_frame_report(final_data, output_folder)
#split_video_pro(video_in, csv_log, seg_folder)

# Then create your ghost video:
#create_grayscale_ghost_video(seg_folder, csv_log, ghost_out2, num_segments=12, mode="lighten")
#create_temporal_ghost_video(seg_folder, csv_log, ghost_out, num_segments=12)
#combine_ghost_videos(ghost_out2, ghost_out, hybrid_out, mode="overlay", opacity=0.6)

# For slightly different color and version, Try mode="hardlight" at opacity=0.7 instead, 