"""Transparent portfolio review rules. No trade signals or forecasts."""
from __future__ import annotations
from datetime import date, timedelta


def review(snapshot: dict, reports: dict | None = None) -> list[dict]:
    reports = reports or {}
    items = []
    for p in snapshot.get('positions', []):
        reasons = []
        weight = float(p.get('weight', 0))
        if weight >= 30:
            reasons.append(f"계좌 내 보유 비중 {weight:.1f}% · 집중도 확인")
        report = reports.get(p['code'], {})
        recent = [d for d in report.get('disclosures', [])
                  if str(d.get('date', '')) >= (date.today() - timedelta(days=7)).strftime('%Y%m%d')]
        if recent:
            reasons.append(f"최근 7일 공시 {len(recent)}건 · 원문 확인")
        years = report.get('years') or []
        if len(years) >= 2 and years[-1].get('profit') is not None and years[-2].get('profit') is not None:
            current, previous = years[-1]['profit'], years[-2]['profit']
            if current < previous:
                reasons.append(f"결산 영업이익 {previous:,.0f}억 → {current:,.0f}억 · 전년 대비 감소")
        if not report:
            reasons.append('재무·공시 미연결 · 계좌 자료만 확인')
        items.append({'code': p['code'], 'name': p['name'], 'weight': weight,
                      'reasons': reasons, 'priority': (weight >= 30) * 2 + bool(recent) + any('영업이익' in x for x in reasons)})
    return sorted(items, key=lambda x: (-x['priority'], -x['weight'], x['code']))

