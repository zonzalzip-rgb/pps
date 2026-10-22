"""Collect user-requested TikTok sources, keeping durable per-file provenance."""
import json
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from download import download

root=Path(sys.argv[1]).resolve()
batch=json.loads((root/'batch.json').read_text(encoding='utf-8'))

def collect(product):
    folder=root/product['slug']
    folder.mkdir(parents=True,exist_ok=True)
    request=dict(product,voice=batch['voice'],footage_mode='auto',product_page_status='Browser returned access-restricted page; product naming from original YouTube product tag or linked catalog')
    (folder/'request.json').write_text(json.dumps(request,ensure_ascii=False,indent=2),encoding='utf-8')
    results=[]
    for idx,url in enumerate(product['sources'],1):
        dest=folder/'footage'/f'{idx:02d}.mp4'
        record=dict(url=url,file=f'footage/{idx:02d}.mp4')
        if dest.is_file() and dest.stat().st_size>1000:
            record['status']='downloaded'
        else:
            try:
                download(url,dest)
                record['status']='downloaded'
            except Exception as exc:
                record['status']='failed'
                record['error']=str(exc)[:200]
        results.append(record)
        (folder/'sources.json').write_text(json.dumps(dict(query_zh=product['query_zh'],videos=results),ensure_ascii=False,indent=2),encoding='utf-8')
        print(product['number'],idx,record['status'],flush=True)
    count=sum(x['status']=='downloaded' for x in results)
    return product['number'],count

with ThreadPoolExecutor(max_workers=3) as pool:
    for future in as_completed([pool.submit(collect,p) for p in batch['products']]):
        print('PRODUCT READY:',future.result(),flush=True)
