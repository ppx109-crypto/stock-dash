"""Local learning ledger using dated closing prices; never sends broker orders."""
import copy
import json
import re
import uuid
from datetime import date,datetime

class PaperError(ValueError):
    pass

def whole(value,label,minimum=1,maximum=1_000_000_000):
    if isinstance(value,bool) or not isinstance(value,int) or not minimum<=value<=maximum:
        raise PaperError(f'{label} 값을 확인하세요.')
    return value

def new_account(initial=10_000_000):
    return {'version':1,'initial':whole(initial,'시작 자금'),'trades':[]}

def replay(account):
    initial=whole(account.get('initial'),'시작 자금')
    trades=account.get('trades')
    if account.get('version')!=1 or not isinstance(trades,list) or len(trades)>1000:
        raise PaperError('모의투자 기록 형식을 확인하세요.')
    cash=initial;realized=0;positions={};ids=set()
    for trade in trades:
        if not isinstance(trade,dict):raise PaperError('거래 기록 형식을 확인하세요.')
        code=trade.get('code','');side=trade.get('side');identifier=trade.get('id')
        if not isinstance(code,str) or not re.fullmatch(r'[0-9]{6}',code) or side not in ('buy','sell'):
            raise PaperError('모의 거래 종목·매매 구분을 확인하세요.')
        if not isinstance(identifier,str) or not identifier or identifier in ids:raise PaperError('중복 거래 기록입니다.')
        ids.add(identifier)
        price=whole(trade.get('price'),'가격');quantity=whole(trade.get('quantity'),'수량',maximum=1_000_000)
        if not isinstance(trade.get('name'),str) or len(trade['name'])>100 or not isinstance(trade.get('note',''),str) or len(trade.get('note',''))>500:
            raise PaperError('종목명·매매 메모를 확인하세요.')
        try:
            quote=date.fromisoformat(trade['price_date']);stamp=datetime.fromisoformat(trade['at'])
            if not 0<=(stamp.date()-quote).days<=5:raise ValueError
        except (KeyError,TypeError,ValueError):raise PaperError('종가 기준일과 모의 거래 시점을 확인하세요.') from None
        position=positions.setdefault(code,{'code':code,'name':trade['name'],'quantity':0,'cost':0})
        value=price*quantity
        if side=='buy':
            if value>cash:raise PaperError('가상 현금이 부족합니다.')
            cash-=value;position['quantity']+=quantity;position['cost']+=value
        else:
            if quantity>position['quantity']:raise PaperError('보유수량보다 많이 매도할 수 없습니다.')
            # Allocate integer-won weighted cost; full exits remove all residual cost.
            cost=position['cost'] if quantity==position['quantity'] else (position['cost']*quantity+position['quantity']//2)//position['quantity']
            position['quantity']-=quantity;position['cost']-=cost;cash+=value;realized+=value-cost
    return {'cash':cash,'realized':realized,'positions':[p for p in positions.values() if p['quantity']>0]}

def execute(account,code,name,side,quantity,price,price_date,at,note='',identifier=None):
    result=copy.deepcopy(account)
    result['trades'].append({'id':identifier or str(uuid.uuid4()),'code':code,'name':name,'side':side,
        'quantity':quantity,'price':price,'price_date':price_date,'at':at,'note':note})
    replay(result)
    return result

def export_account(account):
    replay(account)
    return json.dumps(account,ensure_ascii=False,indent=2)

def restore_account(payload):
    if len(payload)>1_000_000:raise PaperError('백업 파일은 1MB 이하여야 합니다.')
    try:account=json.loads(payload)
    except (TypeError,ValueError):raise PaperError('모의투자 JSON 백업 파일을 확인하세요.') from None
    if not isinstance(account,dict):raise PaperError('모의투자 기록 형식을 확인하세요.')
    replay(account)
    return account

