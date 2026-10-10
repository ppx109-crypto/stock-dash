"""자리표시자를 합성 값으로(메모리 안에서만). 세션 주소 모양은 조각을 이어 만듦."""
import hashlib, json
def values(fid):
    h = hashlib.sha256(f"RELEASE-0001|{fid}".encode()).hexdigest()
    host = "claude" + ".ai/code/" + "sess" + "ion_"
    return {"{{URL}}": "https://" + host + "SYN" + h[:20],
            "{{HOSTUP}}": "https://" + host.replace("claude.ai", "Claude.AI") + "SYN" + h[20:40],
            "{{TRAILER}}": "Claude-" + "Session: https://" + host + "SYN" + h[40:60]}
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
            return {k: sub(v) for k, v in x.items()}
        return x
    return sub(fx["data"])
def all_secrets(fids):
    return sorted({v for i in fids for v in values(i).values()} | {v.split(": ", 1)[1] for i in fids for k, v in values(i).items() if k == "{{TRAILER}}"})
