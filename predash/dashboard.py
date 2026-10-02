"""Evidence-first overview: one distinct item per section, no invented facts."""
from datetime import date, timedelta

def overview(snapshot, reports, today=None):
    today=today or date.today()
    positions=sorted(snapshot.get('positions',[]),key=lambda p:-p['weight'])
    largest=positions[0] if positions else None
    earnings=None
    for position in positions:
        report=reports.get(position['code'],{})
        years=report.get('years') or []
        if len(years)>=2 and all(y.get('profit') is not None for y in years[-2:]):
            earnings={'position':position,'report':report,'previous':years[-2], 'current':years[-1]}
            break
    disclosure=None
    cutoff=(today-timedelta(days=7)).strftime('%Y%m%d')
    options=[]
    for position in positions:
        report=reports.get(position['code'],{})
        for item in report.get('disclosures',[]):
            if cutoff<=str(item.get('date',''))<=today.strftime('%Y%m%d'):
                options.append({'position':position,'item':item,'report':report})
    if options: disclosure=max(options,key=lambda row:row['item']['date'])
    return {'largest':largest,'earnings':earnings,'disclosure':disclosure,
            'position_count':len(positions),'report_count':len(reports)}

def latest_held_buy(snapshot, fills):
    """Latest observed buy for a currently held code, not a claimed open lot."""
    held={p['code'] for p in snapshot.get('positions',[])}
    return max((f for f in fills if f['side']=='buy' and f['code'] in held),
               key=lambda f:f['at'],default=None)

