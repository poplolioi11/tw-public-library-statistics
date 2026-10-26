"""Maintainer-reviewed phase1 layers; deliberately separate from canonical cohorts."""
import hashlib,json,re
from pathlib import PurePosixPath
NAME='reviewed_phase1_batches.json'

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None

def relative(name,allowed=('raw','derived','scripts','research','data')):
    p=PurePosixPath(name)
    if p.is_absolute() or '..' in p.parts or not p.parts or p.parts[0] not in allowed:
        raise ValueError('Phase1 path must remain in the declared project layer: '+name)
    return name

def load(root):
    path=root/'data'/NAME
    if not path.exists():return None
    d=json.loads(path.read_text())
    if d.get('schema_version')!='1.0.0' or d.get('canonical_union_permitted') is not False:
        raise ValueError('Unknown/unsafe phase1 registry schema')
    ids=set();outputs=set()
    for g in d['batches']:
        if not re.fullmatch(r'[a-z0-9_]+',g['id']) or g['id'] in ids:raise ValueError('Duplicate/invalid phase1 batch')
        ids.add(g['id'])
        if g['review_status']!='source_reviewed':raise ValueError('Unreviewed phase1 batch cannot run')
        if not re.fullmatch(r'[A-Za-z0-9_]+\.py',g['script']):raise ValueError('Phase1 extractor must be a local Python filename')
        for x in g['originals']:
            relative(x['path'],('raw',))
            if not re.fullmatch('[a-f0-9]{64}',x['sha256']):raise ValueError('Every original needs its exact reviewed SHA')
        for x in g['inputs']:relative(x)
        for x in g['outputs']:relative(x,('raw','derived'))
        if outputs.intersection(g['outputs']):raise ValueError('Phase1 batches may not overwrite each other')
        outputs.update(g['outputs'])
    return d

def content_hashes(root):
    registry=load(root)
    if registry is None:return None
    files=set()
    for pattern in registry.get('content_inputs',[]):
        relative(pattern)
        files.update(p for p in root.glob(pattern) if p.is_file() and '.private' not in p.as_posix())
    return {str(p.relative_to(root)):digest(p) for p in sorted(files)}

def content_digest(root):
    values=content_hashes(root)
    return None if values is None else hashlib.sha256(json.dumps(values,sort_keys=True,separators=(',',':')).encode()).hexdigest()
