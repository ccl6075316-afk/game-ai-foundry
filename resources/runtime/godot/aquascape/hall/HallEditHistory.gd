extends RefCounted
## Session-only snapshots; no scene references or save-file writes.
const LIMIT=20
var past: Array=[]
var future: Array=[]

func remember(state: Dictionary) -> void:
    past.append(state.duplicate(true))
    if past.size()>LIMIT:past.pop_front()
    future.clear()

func undo(current: Dictionary) -> Variant:
    if past.is_empty():return null
    future.append(current.duplicate(true))
    return past.pop_back()

func redo(current: Dictionary) -> Variant:
    if future.is_empty():return null
    past.append(current.duplicate(true))
    return future.pop_back()
