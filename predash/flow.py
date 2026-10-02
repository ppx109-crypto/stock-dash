"""Validated KIS investor flow; net-buy quantity, not trading value."""
from datetime import datetime

def summarize_flow(rows,today):
    valid=[];seen=set()
    for row in rows:
        stamp=str(row.get('stck_bsop_date',''))
        try:
            day=datetime.strptime(stamp,'%Y%m%d').date()
            if day>today:continue
            values={key:int(str(row[field]).replace(',','')) for key,field in (
                ('individual','prsn_ntby_qty'),('foreign','frgn_ntby_qty'),('institution','orgn_ntby_qty'))}
        except (ValueError,TypeError,KeyError):continue
        if day in seen:continue
        seen.add(day);valid.append((day,values))
    valid.sort(key=lambda x:x[0],reverse=True)
    if not valid or (today-valid[0][0]).days>5:return None
    latest=valid[0]
    totals={k:0 for k in latest[1]};history=[]
    for day,values in reversed(valid[:20]):
        totals={k:totals[k]+values[k] for k in totals}
        history.append({'date':day.isoformat(),'daily':values,'cumulative':dict(totals)})
    selected=valid[:5]
    return {'date':latest[0].isoformat(),'daily':latest[1],
            'five_day':{key:sum(row[key] for _,row in selected) for key in latest[1]},
            'history':history,'sessions':len(selected),'from':selected[-1][0].isoformat()}

