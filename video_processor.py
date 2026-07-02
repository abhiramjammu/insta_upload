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
        
        random.seed(i)
        for _ in range(8):
            r = random.randint(300, 700)
            x = random.randint(-200, w)
            y = random.randint(-200, h)
            c = random.choice([palette[1], palette[2]])
            draw.ellipse((x, y, x+r*2, y+r*2), fill=(c[0], c[1], c[2], 100))
            
        img = img.resize((270, 480), Image.Resampling.BILINEAR).resize((w, h), Image.Resampling.BICUBIC)
        img.save(path)

def create_rounded_mask(width, height, radius, output_path):
    """Creates a black and white PNG mask with rounded corners."""
    img = Image.new('L', (width, height), 0)
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((0, 0, width, height), radius=radius, fill=255)
    img.save(output_path)

def process_video_ffmpeg(input_path, output_path):
    """Trims video, applies moving pastel background, 75% scale rounded corners, drop shadow, and a progress bar!"""
    bg_dir = os.path.join(os.path.dirname(output_path), "backgrounds")
    generate_backgrounds(bg_dir)
    
    bg_images = [f for f in os.listdir(bg_dir) if f.endswith(".png")]
    selected_bg = os.path.join(bg_dir, random.choice(bg_images))
    
    try:
        probe_cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', input_path]
        dur_str = subprocess.check_output(probe_cmd).decode('utf-8').strip()
        duration = float(dur_str)
    except:
        duration = 10.0

    if duration <= 30:
        trim_duration = 10
    elif duration <= 60:
        trim_duration = 15
    else:
        trim_duration = 30
        
    trim_duration = min(trim_duration, duration)
    
    canvas_w, canvas_h = 1080, 1920
    inner_w = int(canvas_w * 0.75)  # 810
    inner_h = int(canvas_h * 0.75)  # 1440
    
    mask_path = os.path.join(os.path.dirname(output_path), "mask.png")
    create_rounded_mask(inner_w, inner_h, radius=60, output_path=mask_path)
    
    filter_complex = (
        # 1. Format video and scale to 75%
        f"[0:v]trim=duration={trim_duration},setpts=PTS-STARTPTS,format=rgba[v_trim];"
        f"[v_trim]scale={inner_w}:{inner_h}:force_original_aspect_ratio=increase,crop={inner_w}:{inner_h}[v_scaled];"
        
        # 2. Extract mask and merge for rounded corners
        f"[2:v]format=rgba,alphaextract[mask];"
        f"[v_scaled][mask]alphamerge[fg_masked];"
        
        # 3. Create a drop shadow from the rounded video
        f"[fg_masked]split[fg_shadow][fg_main];"
        f"[fg_shadow]colorchannelmixer=rr=0:rg=0:rb=0:ra=0:gr=0:gg=0:gb=0:ga=0:br=0:bg=0:bb=0:ba=0:aa=0.5,scale={inner_w+20}:{inner_h+20},boxblur=20[shadow];"
        
        # 4. Background Animation (Zoom in slowly)
        f"[1:v]zoompan=z='zoom+0.001':d={int(trim_duration*30)}:s={canvas_w}x{canvas_h}[bg_anim];"
        
        # 5. Overlay shadow, then main video
        f"[bg_anim][shadow]overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2+20[bg_with_shadow];"
        f"[bg_with_shadow][fg_main]overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2[base_out];"
        
        # 6. Create attention-grabbing Progress Bar at the bottom of the inner video
        f"color=c=white@0.9:s={inner_w}x12:d={trim_duration}[prog_src];"
        f"[prog_src]scale=w='max(1, (t/{trim_duration})*{inner_w})':h=12:eval=frame[prog_bar];"
        f"[base_out][prog_bar]overlay=(main_w-{inner_w})/2:(main_h+{inner_h})/2-40[outv];"
        
        f"[0:a]atrim=duration={trim_duration},asetpts=PTS-STARTPTS[outa]"
    )
    
    cmd = [
        'ffmpeg', '-y', 
        '-i', input_path, 
        '-i', selected_bg,
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
    
    if os.path.exists(mask_path):
        os.remove(mask_path)
        
    return output_path
