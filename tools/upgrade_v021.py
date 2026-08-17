from pathlib import Path
import base64, zlib


def unpack(parts):
    payload = ''.join(Path(p).read_text('utf-8').strip() for p in parts)
    return zlib.decompress(base64.b64decode(payload))


app_parts = [f'tools/payload_app_{i}.txt' for i in range(1, 6)]
readme_parts = ['tools/payload_readme.txt']

Path('src/app.py').write_bytes(unpack(app_parts))
Path('README.md').write_bytes(unpack(readme_parts))
print('Wrote src/app.py and README.md for v0.2.1')
