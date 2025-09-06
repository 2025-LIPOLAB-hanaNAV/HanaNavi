import os
from typing import Optional

import requests


def download_to(path: str, url: str, timeout: int = 30) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with requests.get(url, stream=True, timeout=timeout) as r:
        r.raise_for_status()
        with open(path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
    return path


def maybe_download(dest_dir: str, filename: str, url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    os.makedirs(dest_dir, exist_ok=True)
    path = os.path.join(dest_dir, filename)
    if not os.path.exists(path):
        return download_to(path, url)
    return path

