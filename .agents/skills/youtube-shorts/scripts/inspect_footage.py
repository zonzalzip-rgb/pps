"""Create a labeled contact sheet for a local footage directory."""
import sys
from pathlib import Path
import cv2
from PIL import Image, ImageDraw

root = Path(sys.argv[1])
tiles = []
for clip in sorted((root / 'footage').glob('[0-9][0-9].mp4')):
    cap = cv2.VideoCapture(str(clip))
    fps = cap.get(cv2.CAP_PROP_FPS)
    duration = cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps if fps else 0
    print(f'{clip.name}: {duration:.2f}s', flush=True)
    row = Image.new('RGB', (5 * 216, 414), '#222222')
    for i, fraction in enumerate([.08, .25, .45, .65, .85]):
        timestamp = duration * fraction
        cap.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
        ok, frame = cap.read()
        if ok:
            img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            img.thumbnail((216, 384))
            row.paste(img, (i * 216 + (216-img.width)//2, 30))
        ImageDraw.Draw(row).text((i*216+5, 5), f'{clip.name} @ {timestamp:.1f}s', fill='white')
    cap.release()
    tiles.append(row)
sheet = Image.new('RGB', (1080, 414 * len(tiles)))
for i, row in enumerate(tiles):
    sheet.paste(row, (0, 414*i))
sheet.save(root / 'footage_contact.jpg')
