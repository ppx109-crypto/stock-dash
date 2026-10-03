# RNA 22라운드(q059 짝): 15분봉용 추세 문 표를 DNA · VX 0.9 · 1.09 · 1.3으로 한 번에(일봉 표 한 번만 읽음 · hlab.daily_tables와 같은 셈)
import pickle, sys
sys.path.insert(0, "/home/user/stock-dash")
import caps, lab, rule, hlab
rows = lab.load()
caps.tag(rows, 150)
edge = hlab.calm_by_month(rows, rule.CALM)
out = {k: {} for k in ("dna", "0.9", "1.09", "1.3")}
for r in rows:
    if r["date"] >= "20220101" and r.get(caps.RANK) and r[caps.RANK] <= rule.TOP:
        vol, th = r.get("변동성"), edge.get(r["date"][:6])
        if th is None or vol is None or vol > th or (r.get("추세 기울기") or -99) < rule.SLOPE:
            continue
        s = r.get("60일 전 대비") or -99
        key = (r["code"], r["date"])
        if s >= rule.SIXTY:
            out["dna"][key] = True
        for z in ("0.9", "1.09", "1.3"):
            if s >= float(z) * vol * 60 ** 0.5:
                out[z][key] = True
for k, v in out.items():
    pickle.dump(v, open(f"{sys.argv[1]}/trend_{k}.pkl", "wb"))
    print(k, len(v))
