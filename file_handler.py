import os
import shutil
from pathlib import Path
from typing import List
import codecs

def list_md_files(folder: str) -> List[str]:
    p = Path(folder)
    return [str(x) for x in p.glob("*.md") if x.is_file()]

def read_md_file(path: str, encoding='utf-8') -> str:
    # fallback encodings could be added if gerekli
    try:
        with codecs.open(path, 'r', encoding=encoding) as f:
            return f.read()
    except Exception:
        with codecs.open(path, 'r', encoding='latin-1', errors='ignore') as f:
            return f.read()

def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def safe_move(src: str, dst: str):
    ensure_dir(os.path.dirname(dst))
    # atomic-ish move on same volume
    shutil.move(src, dst)

def archive_file(src: str, archive_dir: str):
    if not archive_dir:
        return
    ensure_dir(archive_dir)
    dst = os.path.join(archive_dir, Path(src).name)
    safe_move(src, dst)
