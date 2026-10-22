"""Inspect final media metadata and produce visual review sheets."""
import json
import subprocess
import sys
from pathlib import Path
import cv2
from PIL import Image, ImageDraw
sys.path.insert(0, str(Path(__file__).resolve().parent))
import toolpaths

root = Path(sys.argv[1]).resolve()
repo = Path(__file__).resolve().parents[1]
probe = toolpaths.require('ffprobe')['ffprobe']
result = subprocess.run([str(probe), '-v','error','-show_streams','-show_format','-of','json',str(root/'final.mp4')], capture_output=True, encoding='utf-8', check=True)
metadata = json.loads(result.stdout)
video = next(x for x in metadata['streams'] if x['codec_type']=='video')
audio = next(x for x in metadata['streams'] if x['codec_type']=='audio')
duration = float(metadata['format']['duration'])
assert 0 < duration < 30
assert (video['width'],video['height'])==(1080,1920)
assert video['codec_name']=='h264' and audio['codec_name']=='aac'
cap=cv2.VideoCapture(str(root/'final.mp4'))
sheet=Image.new('RGB',(1080,768),'#222222')
for idx,t in enumerate([duration*(i+.5)/8 for i in range(8)]):
    cap.set(cv2.CAP_PROP_POS_MSEC,t*1000)
    ok,frame=cap.read()
    assert ok, f'Cannot decode at {t}s'
    img=Image.fromarray(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)).resize((270,480))
    img.thumbnail((270,354))
    x,y=(idx%4)*270,(idx//4)*384
    sheet.paste(img,(x+(270-img.width)//2,y+30))
    ImageDraw.Draw(sheet).text((x+6,y+7),f'{t:.1f}s',fill='white')
cap.release()
sheet.save(root/'final_review.jpg')
thumbs=Image.new('RGB',(1440,640))
for idx,p in enumerate(sorted((root/'thumbnails').glob('thumb_*.png'))):
    img=Image.open(p)
    assert img.size==(720,1280)
    thumbs.paste(img.resize((360,640)),(idx*360,0))
thumbs.save(root/'thumbnail_review.jpg')
(root/'verification.json').write_text(json.dumps(dict(duration=duration,width=video['width'],height=video['height'],video_codec=video['codec_name'],audio_codec=audio['codec_name'],thumbnail_count=4),indent=2),encoding='utf-8')
print(f'Verified: {duration:.2f}s, 1080x1920, H.264/AAC, 4 thumbnails',flush=True)
