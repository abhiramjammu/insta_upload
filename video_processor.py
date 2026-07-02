import os
import subprocess
from PIL import Image, ImageDraw

def create_rounded_mask(width, height, radius, output_path):
    """Creates a black and white PNG mask with rounded corners."""
    img = Image.new('L', (width, height), 0) # Black background (transparent)
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((0, 0, width, height), radius=radius, fill=255) # White rounded box (opaque)
    img.save(output_path)

def process_video_ffmpeg(input_path, output_path):
    """Trims video, applies blurred background, and rounded corners."""
    import json
    
    # Get video duration using ffprobe
    probe_cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', input_path]
    try:
        dur_str = subprocess.check_output(probe_cmd).decode('utf-8').strip()
        duration = float(dur_str)
    except:
        duration = 10.0 # fallback

    # Trimming logic
    if duration <= 30:
        trim_duration = 10
    elif duration <= 60:
        trim_duration = 15
    else:
        trim_duration = 30
        
    trim_duration = min(trim_duration, duration)
    
    # We will target a 1080x1920 (Vertical/Reels) canvas
    canvas_w, canvas_h = 1080, 1920
    
    # The inner video will be slightly smaller (e.g. 960 width) to show the background
    inner_w = 960
    
    # Generate the mask for the inner video
    mask_path = os.path.join(os.path.dirname(output_path), "mask.png")
    # We don't know the exact inner height until we scale it, but if it maintains aspect ratio:
    # Actually, we can just apply a fixed padding of 60px on all sides.
    # Let's let ffmpeg scale the inner video to width 960, and calculate height.
    # To simplify, we'll create a 960x1706 mask (assuming 9:16 input). 
    create_rounded_mask(inner_w, int(inner_w * 16/9), radius=60, output_path=mask_path)
    
    # FFmpeg complex filter
    # 1. Take input, trim it.
    # 2. Create Background: Scale to 1080x1920, blur it heavily.
    # 3. Create Foreground: Scale to 960 width (keep aspect ratio), apply mask.
    # 4. Overlay Foreground onto Background centered.
    
    filter_complex = (
        f"[0:v]trim=duration={trim_duration},setpts=PTS-STARTPTS[v_trim];"
        f"[v_trim]scale={canvas_w}:{canvas_h}:force_original_aspect_ratio=increase,crop={canvas_w}:{canvas_h},boxblur=40:40[bg];"
        f"[v_trim]scale={inner_w}:-1[fg_scaled];"
        f"[1:v]format=rgba,alphaextract[mask];"
        f"[fg_scaled][mask]alphamerge[fg_masked];"
        f"[bg][fg_masked]overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2[outv];"
        f"[0:a]atrim=duration={trim_duration},asetpts=PTS-STARTPTS[outa]"
    )
    
    cmd = [
        'ffmpeg', '-y', 
        '-i', input_path, 
        '-i', mask_path,
        '-filter_complex', filter_complex,
        '-map', '[outv]', 
        '-map', '[outa]', 
        '-c:v', 'libx264', '-crf', '23', '-preset', 'fast',
        '-c:a', 'aac', '-b:a', '128k',
        output_path
    ]
    
    print(f"Executing FFmpeg to process {input_path}...")
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Cleanup mask
    if os.path.exists(mask_path):
        os.remove(mask_path)
        
    return output_path

if __name__ == "__main__":
    # Test
    # process_video_ffmpeg("test.mp4", "out.mp4")
    pass
