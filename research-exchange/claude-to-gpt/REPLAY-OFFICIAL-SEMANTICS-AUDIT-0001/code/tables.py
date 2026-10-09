import re,html,sys
t=open(sys.argv[1],encoding='utf-8',errors='replace').read()
grep=sys.argv[2] if len(sys.argv)>2 else None
for ti,tb in enumerate(re.findall(r'<table[^>]*>(.*?)</table>',t,re.S)):
    rows=[]
    for r in re.findall(r'<tr[^>]*>(.*?)</tr>',tb,re.S):
        c=[re.sub(r'\s+',' ',html.unescape(re.sub(r'<br\s*/?>',' / ',re.sub(r'<(?!br)[^>]+>',' ',x)))).strip() for x in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>',r,re.S)]
        rows.append(' | '.join(c))
    body='\n'.join(rows)
    if grep and not re.search(grep,body): continue
    print(f'--- 표 {ti} ({len(rows)}줄)'); print(body[:6000])
