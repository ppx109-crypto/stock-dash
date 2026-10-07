"""표준 라이브러리만 쓰는 작은 JSON Schema 검사기(이번 스키마가 쓰는 키워드만: type · required · properties ·
enum · const · pattern · minimum · items). 외부 jsonschema 패키지를 쓰지 않습니다."""
import json, os, re

TYPES = {"object": dict, "array": list, "string": str, "boolean": bool, "null": type(None)}


def _type_ok(v, t):
    ts = t if isinstance(t, list) else [t]
    for x in ts:
        if x == "integer" and isinstance(v, int) and not isinstance(v, bool):
            return True
        if x == "number" and isinstance(v, (int, float)) and not isinstance(v, bool):
            return True
        if x in TYPES and isinstance(v, TYPES[x]) and not (x != "boolean" and isinstance(v, bool)):
            return True
    return False


def check(v, s, path="$"):
    errs = []
    if "type" in s and not _type_ok(v, s["type"]):
        return [f"{path}: type"]
    if "const" in s and v != s["const"]:
        errs.append(f"{path}: const")
    if "enum" in s and v not in s["enum"]:
        errs.append(f"{path}: enum")
    if "pattern" in s and isinstance(v, str) and not re.search(s["pattern"], v):
        errs.append(f"{path}: pattern")
    if "minimum" in s and isinstance(v, (int, float)) and v < s["minimum"]:
        errs.append(f"{path}: minimum")
    if isinstance(v, dict):
        for k in s.get("required", []):
            if k not in v:
                errs.append(f"{path}.{k}: required")
        for k, sub in s.get("properties", {}).items():
            if k in v:
                errs += check(v[k], sub, f"{path}.{k}")
    if isinstance(v, list) and "items" in s:
        for i, x in enumerate(v):
            errs += check(x, s["items"], f"{path}[{i}]")
    return errs


def load(folder):
    out = {}
    for f in sorted(os.listdir(folder)):
        if f.endswith(".schema.json"):
            out[f[:-12]] = json.load(open(os.path.join(folder, f), encoding="utf-8"))
    return out


def check_record(r, schemas):
    errs = check(r, schemas["envelope"])
    pt = (r.get("record_type") or "").lower()
    if pt in schemas:
        errs += check(r.get("payload"), schemas[pt], "$.payload")
    else:
        errs.append("$.record_type: no schema")
    return errs
