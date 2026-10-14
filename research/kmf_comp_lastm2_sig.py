"""COMP-0005 공개 신호 표 — COMP-0004 잠근 신호 표(kmf_comp_lastm_sig.json · sha256 f246815a…)에서만 만듦(새 시장 값 계산 없음).
  M12 s{1.0,1.5} = 그날 M1 · M2 신호가 둘 다 있고 방향이 같으면 M1 행 그대로(진입 885분대 · 손절 s × ATR · 915 정리) · 아니면 없음(GPT #352 · #353 H2)
  M1cap s{1.0,1.5} = M1 행 그대로(위험 한도 상한 15는 비공개 결합 엔진에서 적용 · GPT #353 H3)
python3 research/kmf_comp_lastm2_sig.py → research/kmf_comp_lastm2_sig.json"""
import json, hashlib
from pathlib import Path
HERE = Path(__file__).resolve().parent
SRC = HERE / "kmf_comp_lastm_sig.json"; assert hashlib.sha256(SRC.read_bytes()).hexdigest() == "f246815a80dd79ce1d99f0dfa7ceb5f781bc67b3b7eb8c84dd810b38dd1cbbc5"
S = json.loads(SRC.read_text()); sig = {}
for s in ("1.0", "1.5"):
    m1, m2 = S["sig"][f"M1 s{s}"], S["sig"][f"M2 s{s}"]
    sig[f"M12 s{s}"] = {d: (m1[d] if (m1[d] and m2.get(d) and m1[d][0][1] == m2[d][0][1]) else []) for d in m1}
    sig[f"M1cap s{s}"] = {d: m1[d] for d in m1}
out = {"meta": {**S["meta"], "원천": "kmf_comp_lastm_sig.json", "code_sha256": {"kmf_comp_lastm2_sig.py": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}}, "holes": S["holes"], "sig": sig}
(HERE / "kmf_comp_lastm2_sig.json").write_text(json.dumps(out, ensure_ascii=False))
for k, t in sig.items(): print(k, "신호 날", sum(1 for v in t.values() if v))
