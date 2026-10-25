extends RefCounted
## Read-only appearance inputs shared across fish. No materials/rigs are cached.
## Each scene-entry epoch checks current source bytes once; standalone validators
## without an epoch check on every call. Never persists a stale on-disk derivative.
static var _documents: Dictionary={}
static var _epoch := 0
static var _checked: Dictionary={}
static var _digests: Dictionary={}
static var metrics := {"reads":0,"parses":0,"hits":0,"hash_ms":0.0,"parse_ms":0.0}

static func begin_entry() -> void:
    _epoch+=1
    _checked.clear()
    _digests.clear()

static func sha256(path: String) -> String:
    if _epoch>0 and _digests.has(path):return _digests[path]
    var digest := FileAccess.get_sha256(path)
    if _epoch>0:_digests[path]=digest
    return digest

static func read_json(path: String) -> Variant:
    metrics.reads+=1
    if _epoch>0 and _checked.has(path):
        metrics.hits+=1
        return _documents[path].data
    var started := Time.get_ticks_usec()
    var bytes := FileAccess.get_file_as_bytes(path)
    var context := HashingContext.new();context.start(HashingContext.HASH_SHA256);context.update(bytes)
    var sha := context.finish().hex_encode()
    if _epoch>0:_digests[path]=sha
    metrics.hash_ms+=(Time.get_ticks_usec()-started)/1000.0
    if _documents.has(path) and _documents[path].sha256==sha:
        metrics.hits+=1
    else:
        started=Time.get_ticks_usec()
        var data: Variant=JSON.parse_string(bytes.get_string_from_utf8())
        assert(data!=null,"Invalid appearance JSON: "+path)
        _documents[path]={"sha256":sha,"data":data}
        metrics.parses+=1;metrics.parse_ms+=(Time.get_ticks_usec()-started)/1000.0
    _checked[path]=true
    return _documents[path].data

static func clear() -> void:
    _documents.clear();_checked.clear();_digests.clear();_epoch=0
    metrics={"reads":0,"parses":0,"hits":0,"hash_ms":0.0,"parse_ms":0.0}
