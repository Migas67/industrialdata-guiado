import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path


def root():
    return Path(os.environ.get('DATA_ROOT', 'data')).resolve()


def timestamp(value):
    dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    if dt.tzinfo is None:
        raise ValueError('timezone_required')
    return dt.astimezone(timezone.utc)


def iso(dt):
    return dt.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')


def now():
    return iso(datetime.now(timezone.utc))


def dump(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def identity(*parts):
    return hashlib.sha256('|'.join(map(str, parts)).encode()).hexdigest()[:24]
