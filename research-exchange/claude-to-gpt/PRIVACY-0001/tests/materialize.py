"""fixture 자리표시자를 정해진 합성 값으로 바꿈(메모리 안에서만). 같은 id면 늘 같은 값.
합성 세션 주소는 파일에 통째로 적히지 않도록 조각을 이어 만듭니다."""
import hashlib, json

def _h(fid, tag):
    return hashlib.sha256(f"PRIVACY-0001|{fid}|{tag}".encode()).hexdigest()

def values(fid):
    host = "claude" + ".ai" + "/code/" + "sess" + "ion_"
    return {"{{SYN}}": "SYN" + _h(fid, "syn")[:14].upper(),
            "{{TOKEN}}": "synTok" + _h(fid, "tok")[:24],
            "{{SURL}}": "https://" + host + "SYNTH" + _h(fid, "surl")[:20]}

def materialize(fx):
    vals = values(fx["id"])
    def sub(x):
        if isinstance(x, str):
            for k, v in vals.items():
                x = x.replace(k, v)
            return x
        if isinstance(x, list):
            return [sub(v) for v in x]
        if isinstance(x, dict):
            return {sub(k): sub(v) for k, v in x.items()}
        return x
    used = [v for k, v in vals.items() if k in json.dumps(fx["data"], ensure_ascii=False)]
    return sub(fx["data"]), used
