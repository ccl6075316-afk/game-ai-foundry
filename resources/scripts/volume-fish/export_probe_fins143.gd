extends "export_source_fin_roots141.gd"
## Reproduce severe v7 failures only. Explicit diagnostic, cannot pass490 coverage.
func sample(entry:Dictionary,label:String,seconds:float):
    var cases=JSON.parse_string(FileAccess.get_file_as_string(OS.get_environment("FOUNDRY_FIN_PROBE143_CASES")))
    for row in cases:
        if row[0]==label and abs(float(row[1])-seconds)<.000001:
            super.sample(entry,label,seconds);return
func save_json(path:String,value:Variant):
    if path.ends_with("export.validation.json"):
        value.erase("fin_membrane_revision");value.diagnostic_only=true;value.scope="Selected actual earlier failure poses only, not completion or490 coverage."
    super.save_json(path,value)
