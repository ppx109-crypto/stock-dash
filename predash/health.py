"""Descriptive holding status, never an order or valuation judgement."""
from datetime import datetime,timedelta

def events(report,today):
    result=[]
    for d in (report or {}).get('disclosures',[]):
        try:day=datetime.strptime(str(d.get('date','')),'%Y%m%d').date()
        except ValueError:continue
        if not today-timedelta(days=30)<=day<=today:continue
        title=str(d.get('title',''));compact=title.replace(' ','')
        if any(k in compact for k in ('유상증자','전환사채','신주인수권부사채','자기주식처분')):label='자금조달·주식공급 확인';kind='risk'
        elif any(k in compact for k in ('판매','공급','수주')) and '계약' in compact:label='계약 공시 확인';kind='contract'
        elif '보고서' in compact and any(k in compact for k in ('반기','분기','사업')):label='정기 실적 공시';kind='earnings'
        elif '임원' in compact or '주요주주' in compact:label='내부자 지분변동 확인';kind='ownership'
        else:label='기타 공시';kind='other'
        result.append({**d,'label':label,'kind':kind,'amended':'정정' in title or '해지' in title})
    return sorted(result,key=lambda x:(x['kind']=='other',-int(x['date'])))

def status(position,report,today,upper=10,lower=-5):
    cost=position.get('average_cost',0)*position.get('quantity',0)
    rate=position.get('pnl',0)/cost*100 if cost>0 else None
    price='손익률 보류' if rate is None else '수익 기준 도달' if rate>=upper else '손실 기준 도달' if rate<=lower else '수익 중' if rate>0 else '손실 중' if rate<0 else '손익 보합'
    m=(report or {}).get('metrics');growth=None;earnings='최근 동기 실적 보류'
    if m:
        old,new=m.get('prior_profit'),m.get('profit')
        if old is not None and new is not None:
            if old<0 and new>0:earnings='흑자 전환'
            elif old>0 and new<0:earnings='적자 전환'
            elif old<=0:earnings='적자 축소' if new>old else '적자 확대' if new<old else '이익 동일'
            else:
                growth=(new/old-1)*100
                earnings='이익 급증' if growth>=30 else '이익 증가' if growth>5 else '이익 감소' if growth< -5 else '이익 정체'
    notices=events(report,today)
    reasons=[f"비중 {position.get('weight',0):.1f}%",price,earnings]
    if position.get('weight',0)>=30:reasons.append('단일종목 집중도 확인')
    if notices:reasons.append(notices[0]['label']+' · 원문 확인')
    return {'rate':rate,'price':price,'earnings':earnings,'growth':growth,'events':notices,'summary':' · '.join(reasons),
            'warning':rate is not None and rate<=lower,'growing':earnings in ('이익 증가','이익 급증','흑자 전환')}

