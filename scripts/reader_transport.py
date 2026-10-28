"""Lossless embedded JSON for complete portable readers; not an observation layer."""
import base64,gzip,hashlib,json


def encode(payload,threshold=80*1024*1024):
    body=json.dumps(payload,ensure_ascii=False,separators=(',',':')).encode()
    if len(body)<threshold:return body.decode()
    envelope={'reader_transport':'gzip-base64-json-1','uncompressed_bytes':len(body),
              'uncompressed_sha256':hashlib.sha256(body).hexdigest(),
              'payload_base64':base64.b64encode(gzip.compress(body,compresslevel=9,mtime=0)).decode()}
    return json.dumps(envelope,separators=(',',':'))


def decode(text):
    obj=json.loads(text)
    if not isinstance(obj,dict) or 'reader_transport' not in obj:return obj
    if obj['reader_transport']!='gzip-base64-json-1':raise ValueError('Unknown portable-reader transport')
    if not isinstance(obj.get('uncompressed_bytes'),int) or not 0<obj['uncompressed_bytes']<=512*1024*1024:raise ValueError('Invalid portable-reader length')
    body=gzip.decompress(base64.b64decode(obj['payload_base64'],validate=True))
    if len(body)!=obj['uncompressed_bytes'] or hashlib.sha256(body).hexdigest()!=obj['uncompressed_sha256']:raise ValueError('Portable-reader data length or SHA differs')
    return json.loads(body)
