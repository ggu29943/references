"""Package source, references, models and review evidence after build/validation."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output'
required = ['Yuan_Character.blend', 'Yuan_Base.fbx', 'Yuan_Winged.fbx',
            'Yuan_Base_LOD1.fbx', 'Yuan_Base_LOD2.fbx', 'Yuan_Winged_LOD1.fbx',
            'Yuan_Winged_LOD2.fbx', 'preview_portrait.png', 'preview_front.png',
            'preview_back.png', 'preview_winged.png', 'check_blink.png',
            'check_arm_pose.png', 'fbx_roundtrip_validation.json', 'prop_validation.json',
            'Yuan_Wings_Fold.fbx', 'Caiheng_Sword.fbx','Caiheng_Sheath.fbx','Caiheng_Tassel.fbx',
            'Caiheng_Text_Sword.fbx','Caiheng_Text_Sheath.fbx',
            'preview_folded.png','preview_weapon.png','preview_weapon_detail.png',
            'Yuan_Wings_Only.fbx','Yuan_Wings_Only_LOD1.fbx','Yuan_Wings_Only_LOD2.fbx']
for name in required:
    if not (OUT / name).is_file():
        raise FileNotFoundError(f'Missing deliverable: {name}')
checks = json.loads((OUT / 'fbx_roundtrip_validation.json').read_text())+json.loads((OUT / 'prop_validation.json').read_text())
if not all(r['pass'] for r in checks):
    raise RuntimeError('FBX validation must pass before packaging')
files = sorted(p for p in ROOT.rglob('*') if p.is_file()
               and '.git' not in p.parts and '__pycache__' not in p.parts
               and p.suffix not in {'.zip', '.blend1', '.blend2', '.log'}
               and p.name != 'SHA256SUMS.json')
manifest = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
(OUT / 'SHA256SUMS.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
files.append(OUT / 'SHA256SUMS.json')
archive = OUT / 'Yuan_Unreal_Package.zip'
with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for p in files:
        z.write(p, Path('Yuan') / p.relative_to(ROOT))
print(f'{archive}: {archive.stat().st_size / 1024**2:.1f} MiB, {len(files)} files')
