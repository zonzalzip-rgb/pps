"""Record source eligibility based on video decoding and editorial review."""
import json
import sys
from pathlib import Path
import cv2

root=Path(sys.argv[1]).resolve()
batch=json.loads((root/'batch.json').read_text(encoding='utf-8-sig'))
report=[]
for product in batch['products']:
    folder=root/product['slug']
    source_path=folder/'sources.json'
    sources=json.loads(source_path.read_text(encoding='utf-8'))
    eligible=0
    for record in sources['videos']:
        clip=folder/record['file']
        record['eligible']=False
        if record['status']=='downloaded' and clip.is_file():
            cap=cv2.VideoCapture(str(clip))
            fps=cap.get(cv2.CAP_PROP_FPS)
            duration=cap.get(cv2.CAP_PROP_FRAME_COUNT)/fps if fps else 0
            cap.set(cv2.CAP_PROP_POS_MSEC,max(0,duration*.4)*1000)
            ok,frame=cap.read()
            cap.release()
            record['duration_sec']=round(duration,3)
            record['eligible']=bool(ok and duration>=2 and frame.std()>2)
            if not record['eligible']:
                record['rejection_reason']='Blank or unusably short video'
            if product['number']=='10' and clip.name=='02.mp4':
                record['eligible']=False
                record['rejection_reason']='Appears to be synthetic presenter footage; use real product demonstrations instead'
        eligible+=record['eligible']
    source_path.write_text(json.dumps(sources,ensure_ascii=False,indent=2),encoding='utf-8')
    assert eligible>=5, f"{product['number']}: only {eligible} eligible videos"
    report.append(dict(number=product['number'],eligible_sources=eligible,query_zh=product['query_zh']))
    print(product['number'],eligible,'eligible sources',flush=True)
(root/'source_audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
