import os
import subprocess

trim_duration = 5

filter_complex = (
    # 1. Format video and scale to 75%
    f"[0:v]trim=duration={trim_duration},setpts=PTS-STARTPTS,scale=810:1440:force_original_aspect_ratio=increase,crop=810:1440,format=rgba[v_scaled];"
    
    # 2. Extract mask and merge for true rounded corners
    f"[2:v]format=rgba[mask];"
    f"[v_scaled][mask]alphamerge[fg_masked];"
    
    # 3. Background Animation
    f"[1:v]zoompan=z='zoom+0.003':d={int(trim_duration*30)}:s=1080x1920[bg_anim];"
    
    # 4. Overlay main video perfectly centered
    f"[bg_anim][fg_masked]overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2[base_out];"
    
    # 5. Draw transparent text outline for each letter to animate tracking
    # 'i' is center
    f"[base_out]drawtext=fontfile='C\\:/Windows/Fonts/arialbd.ttf':text='i':fontcolor=black@0:bordercolor=white@0.5:borderw=8:fontsize=200:x='(w-tw)/2':y='(h-th)/2'[t_i];"
    # 'd' goes left
    f"[t_i]drawtext=fontfile='C\\:/Windows/Fonts/arialbd.ttf':text='d':fontcolor=black@0:bordercolor=white@0.5:borderw=8:fontsize=200:x='(w-tw)/2 - (120 + (t/{trim_duration})*150)':y='(h-th)/2'[t_d];"
    # 't' goes right
    f"[t_d]drawtext=fontfile='C\\:/Windows/Fonts/arialbd.ttf':text='t':fontcolor=black@0:bordercolor=white@0.5:borderw=8:fontsize=200:x='(w-tw)/2 + (120 + (t/{trim_duration})*150)':y='(h-th)/2'[t_t];"
    # '3' goes far left
    f"[t_t]drawtext=fontfile='C\\:/Windows/Fonts/arialbd.ttf':text='3':fontcolor=black@0:bordercolor=white@0.5:borderw=8:fontsize=200:x='(w-tw)/2 - 2*(120 + (t/{trim_duration})*150)':y='(h-th)/2'[t_3];"
    # 'z' goes far right
    f"[t_3]drawtext=fontfile='C\\:/Windows/Fonts/arialbd.ttf':text='z':fontcolor=black@0:bordercolor=white@0.5:borderw=8:fontsize=200:x='(w-tw)/2 + 2*(120 + (t/{trim_duration})*150)':y='(h-th)/2'[outv]"
)

cmd = [
    'ffmpeg', '-y', 
    '-i', r'D:\adobe premiere pro 2025\ANVAYA 5 .mp4', 
    '-loop', '1', '-i', r'D:\insta upload\backgrounds\bg_0.png',
    '-i', r'D:\insta upload\mask.png',
    '-filter_complex', filter_complex,
    '-map', '[outv]', 
    '-t', str(trim_duration),
    '-c:v', 'libx264',
    r'D:\insta upload\static\preview_test.mp4'
]

print("Running...")
subprocess.run(cmd)
print("Done")
