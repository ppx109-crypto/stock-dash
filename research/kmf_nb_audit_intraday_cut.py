import importlib.util, random, collections, copy
P='/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/nbr/research/kmf_nb.py'
def load():
    s=importlib.util.spec_from_file_location('k',P); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
full=load(); M=load()
random.seed(1)
def bots(m):
    b={"R0":lambda d:m.sig_r0(d)}
    for N in (4,8):
        for s in (1.0,1.5): b[f"T1{N}{s}"]=(lambda N,s:lambda d:m.sig_t(d,"T1",N,s))(N,s)
    for s in (1.0,1.5): b[f"T2{s}"]=(lambda s:lambda d:m.sig_t(d,"T2",s=s))(s)
    return b
bad=0; n=0
days=[d for d in full.DAYS if d>='20260306']
for trial in range(120):
    d=random.choice(days); X=random.randrange(560,930)
    i=full.DAYS.index(d)
    BY={dd:dict(full.BY[dd]) for dd in full.DAYS[:i+1]}
    BY[d]={mm:r for mm,r in BY[d].items() if mm<X}
    M.BY=collections.defaultdict(dict,BY); M.DAYS=sorted(BY)
    M.B15=M.bars(15); M.E10=M.ind(M.B15,10); M.E20=M.ind(M.B15,20)
    M.BYD=collections.defaultdict(list)
    for j,b in enumerate(M.B15): M.BYD[b[0]].append(j)
    bf=bots(full); bc=bots(M)
    for k in bf:
        for dl in (0,1,2):
            lf=[]; lc=[]
            full.execute(d,bf[k](d),delay=dl,log=lf); M.execute(d,bc[k](d),delay=dl,log=lc)
            # trades decided (entered) before X: entry same; if exit minute < X (and fill known before X) must be same
            ef=[(t['진입분'],t['진입가'],t['방향']) for t in lf if t['진입분']<X]
            ec=[(t['진입분'],t['진입가'],t['방향']) for t in lc if t['진입분']<X]
            n+=1
            if ef!=ec: bad+=1; print('ENTRY DIFF',d,X,k,dl,ef,ec)
            for a,b in zip(lf,lc):
                if a['정리분']<X-1 and a['사유']!='하루멈춤' and (a['정리분'],a['정리가'])!=(b['정리분'],b['정리가']): bad+=1; print('EXIT DIFF',d,X,k,dl,a,b)
print('checks',n,'bad',bad)
