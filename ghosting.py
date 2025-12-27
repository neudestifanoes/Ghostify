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

        # demux() gives us access to 'packets' (compressed data) to get byte size
        for packet in container.demux(video=0):
            # decode() turns those packets into 'frames' (raw pixels) to get frame type
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

def create_solid_ghost_video(segments_dir, csv_path, output_file, mode="darken"):
    """
    Layers segments using comparative blending (darken/lighten).
    - tpad: Extends the short final segment to match the others, this is bc the last segment did not have 
    90 frames so we needed to pad it up
    - blend: Compares pixels across all segments to keep cars solid while background stays static.
    """
    df = pd.read_csv(csv_path)
    total_frames = len(df)
    last_iframe_idx = df[df['type'] == 'I']['index'].max()
    
    # Handle the short 11th segment by cloning its last frame
    frames_in_last = total_frames - last_iframe_idx
    padding_needed = 90 - frames_in_last 
    
    input_args = []
    for i in range(12): # Assuming 12 segments based on your previous data
        file_path = os.path.join(segments_dir, f"segment_{i:03d}.mp4")
        input_args.extend(["-i", file_path])

    # Build the blend chain filter
    filter_parts = [f"[11:v]tpad=stop={padding_needed}:stop_mode=clone[v11_padded]"]
    last_label = "[0:v]"
    for i in range(1, 11):
        next_label = f"[b{i}]"
        filter_parts.append(f"{last_label}[{i}:v]blend=all_mode={mode}{next_label}")
        last_label = next_label
        
    filter_parts.append(f"{last_label}[v11_padded]blend=all_mode={mode}[outv]")
    filter_complex = "; ".join(filter_parts)

    cmd = [
        "ffmpeg", "-y"
    ] + input_args + [
        "-filter_complex", filter_complex,
        "-map", "[outv]", "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
        output_file
    ]

    print(f"Generating Composite (Mode: {mode})...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"Success! Final ghost video: {output_file}")
    else:
        print("FFmpeg Error:\n", result.stderr)



# Make sure you set ur own path 
video_in = "/Users/neudestifanoes/desktop/ghostify/thevideo.mp4"
csv_log = "video_analysis.csv"
output_folder = "/Users/neudestifanoes/desktop/ghostify"
seg_folder = "/Users/neudestifanoes/desktop/ghostify/segments_fixed"
ghost_out = "/Users/neudestifanoes/desktop/ghostify/solid_ghost_roundabout.mp4"

# ALl function calls are down here and for each step, make sure to comment the one above it so you don't have multiple duplicates
# of CSV and segmented videos

# Uncoment both of these to analyze the video and save the CSV
#final_data = analyze_video(video_in)                                     
#if 'final_data' in locals(): save_frame_report(final_data, output_folder) 

# Uncomment this to chop video into segments
#split_video_pro(video_in, csv_log, seg_folder)                          

# Uncomment this to create final ghost video
#create_solid_ghost_video(seg_folder, csv_log, ghost_out, mode="darken")  