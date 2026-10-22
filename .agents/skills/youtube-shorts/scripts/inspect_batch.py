"""Create one contact sheet per product using the existing inspector."""
import json
import subprocess
import sys
from pathlib import Path
root=Path(sys.argv[1]).resolve()
batch=json.loads((root/'batch.json').read_text(encoding='utf-8'))
for product in batch['products']:
    folder=root/product['slug']
    print(product['slug'],flush=True)
    subprocess.run([sys.executable,str(Path(__file__).with_name('inspect_footage.py')),str(folder)],check=True)
