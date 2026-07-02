import os
import random
import subprocess
from PIL import Image, ImageDraw
import math

def generate_backgrounds(bg_dir):
    """Generates 5 aesthetic pastel bokeh backgrounds if they don't exist."""
    os.makedirs(bg_dir, exist_ok=True)
    colors = [
        # Base Color, Highlight 1, Highlight 2
        ((255, 179, 186), (255, 223, 186), (255, 255, 186)), # Pink/Orange/Yellow
        ((186, 255, 201), (186, 225, 255), (255, 179, 186)), # Green/Blue/Pink
        ((186, 225, 255), (200, 190, 255), (255, 223, 186)), # Blue/Purple/Orange
        ((255, 223, 186), (255, 255, 186), (186, 255, 201)), # Orange/Yellow/Green
        ((240, 230, 255), (255, 204, 229), (204, 229, 255)), # Pastel Purple/Pink/Blue
    ]
    
    for i, palette in enumerate(colors):
        path = os.path.join(bg_dir, f"bg_{i}.png")
        if os.path.exists(path):
            continue
            
        w, h = 1080, 1920
        img = Image.new('RGB', (w, h), palette[0])
        draw = ImageDraw.Draw(img, "RGBA")
        
        # Draw some big soft circles (bokeh/abstract shapes)
        import random
        random.seed(i)
        for _ in range(8):
            r = random.randint(300, 700)
            x = random.randint(-200, w)
            y = random.randint(-200, h)
            c = random.choice([palette[1], palette[2]])
            # Translucent
            draw.ellipse((x, y, x+r*2, y+r*2), fill=(c[0], c[1], c[2], 100))
            
        # Apply a simple blur by resizing down and up
        img = img.resize((270, 480), Image.Resampling.BILINEAR).resize((w, h), Image.Resampling.BICUBIC)
        img.save(path)

def create_rounded_mask(width, height, radius, output_path):
    """Creates a black and white PNG mask with rounded corners."""
    img = Image.new('L', (width, height), 0) # Black background (transparent)
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((0, 0, width, height), radius=radius, fill=255) # White rounded box (opaque)
    img.save(output_path)

def process_video_ffmpeg(input_path, output_path):
    """Trims video, applies moving pastel background, and 75% scale rounded corners."""
    import json
    
    # Generate backgrounds if needed
    bg_dir = os.path.join(os.path.dirname(output_path), "backgrounds")
    generate_backgrounds(bg_dir)
    
    # Pick a random background
    bg_images = [f for f in os.listdir(bg_dir) if f.endswith(".png")]
    selected_bg = os.path.join(bg_dir, random.choice(bg_images))
    
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
    
    # Canvas is 1080x1920
    canvas_w, canvas_h = 1080, 1920
    
    # Inner video is scaled to 75% of the canvas
    inner_w = int(canvas_w * 0.75)  # 810
    inner_h = int(canvas_h * 0.75)  # 1440
    
    # Generate the mask for the inner video
    mask_path = os.path.join(os.path.dirname(output_path), "mask.png")
    create_rounded_mask(inner_w, inner_h, radius=60, output_path=mask_path)
    
    # FFmpeg complex filter
    # 0: Video Input, 1: Background Image, 2: Mask Image
    # 1. Trim Video
    # 2. Scale Video to 810x1440 (Crop to fit 9:16)
    # 3. Apply Mask to Video
    # 4. Animate Background (zoompan to give it slow motion)
    # 5. Overlay Video on Background
    
    filter_complex = (
        f"[0:v]trim=duration={trim_duration},setpts=PTS-STARTPTS[v_trim];"
        f"[v_trim]scale={inner_w}:{inner_h}:force_original_aspect_ratio=increase,crop={inner_w}:{inner_h}[v_scaled];"
        f"[2:v]format=rgba,alphaextract[mask];"
        f"[v_scaled][mask]alphamerge[fg_masked];"
        f"[1:v]zoompan=z='min(zoom+0.0005,1.5)':d={trim_duration*30}:s={canvas_w}x{canvas_h}[bg_anim];"
        f"[bg_anim][fg_masked]overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2[outv];"
        f"[0:a]atrim=duration={trim_duration},asetpts=PTS-STARTPTS[outa]"
    )
    
    cmd = [
        'ffmpeg', '-y', 
        '-i', input_path, 
        '-loop', '1', '-i', selected_bg,
        '-i', mask_path,
        '-filter_complex', filter_complex,
        '-map', '[outv]', 
        '-map', '[outa]', 
        '-c:v', 'libx264', '-crf', '23', '-preset', 'fast',
        '-c:a', 'aac', '-b:a', '128k',
        '-shortest',
        output_path
    ]
    
    print(f"Executing FFmpeg to process {input_path}...")
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Cleanup mask
    if os.path.exists(mask_path):
        os.remove(mask_path)
        
    return output_path
