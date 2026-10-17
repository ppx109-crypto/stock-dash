"""DART 단일판매 · 공급계약 공시 본문 칸 뽑기 판 k2(collect_dart_contracts.parse = k1은 그대로 둠).

k1의 문제(2026-10-17 원문 대조로 확인):
- k1은 원문을 줄로 편 뒤 '칸 이름 뒤 첫 숫자'를 찾음. 정정 공시 맨 앞 '정정사항' 표는 한 칸 안에
  '2. 계약내역 / 계약금액(원) / 매출액대비(%)'가 <br>로 쌓여 있고, 옆 칸에 '정정전 금액 / 정정전 %'가 쌓여 있음.
  줄로 펴면 '매출액대비(%) | 1,402,370,333,636'처럼 % 이름 옆에 정정전 금액이 붙어 % 칸에 금액(1.4e12)이 들어감.
- 조건부 계약 양식은 '확정 계약금액'이 '계약금액 총액(원)'보다 먼저 나와 k1이 총액 대신 확정 금액을 잡음.

k2 규칙:
1. 원문 HTML을 표 → 행 → 칸으로 읽음(줄로 펴지 않음). 칸 이름과 값은 **같은 행의 바로 옆 칸**(또는 같은 칸 안
   '이름 : 값')에서만 잡음. 값 칸이 숫자 하나가 아니면(여러 줄 · 글) 잡지 않고 이유를 적음.
2. '%' 칸은 0 ~ 1000 범위 검사. 넘으면 계약금액 ÷ 최근매출액 × 100 검산이 맞을 때만 두고(원문에 1,237.67처럼
   실제로 큰 값이 있음), 아니면 None + 이유.
3. 금액 단위: 칸 이름 괄호 또는 표 안 '단위 :' 표기(원 · 천원 · 백만원 · 억원)를 원으로 환산. 외화 단위는 None + 이유.
4. 정정 공시: 정정사항 표의 '정정후' 열을 읽음. 본문(정정 뒤 전체 양식)이 있으면 본문 값을 쓰고, 정정후 값과
   다르면 정정후 값을 쓰며 이유를 남김. 본문에 없으면 정정후 값을 씀. '정정전' 값은 쓰지 않음.
5. 해지 공시: '해지금액'은 따로 '해지금액' 칸에 둠(계약금액에 섞지 않음).
"""
import re
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser

PARSER = "k2"
KEYS = ("계약금액", "최근매출액", "매출액대비%", "시작일", "종료일", "상대", "해지금액")
PCT_MAX = Decimal(1000)
UNITS = {"원": 1, "천원": 1000, "백만원": 1000000, "억원": 100000000}
CELL_TAGS = {"td", "th", "te", "tu"}
BREAK_TAGS = {"br", "p", "div"}


class _Tables(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables, self.row, self.cell, self.skip = [], None, None, 0

    def handle_starttag(self, tag, attrs):
        if tag in ("style", "script"):
            self.skip += 1
        elif tag == "table":
            self.tables.append([])
            self.row = None
        elif tag == "tr":
            if not self.tables:
                self.tables.append([])
            self.row = []
            self.tables[-1].append(self.row)
        elif tag in CELL_TAGS:
            if self.row is None:
                self.handle_starttag("tr", [])
            self.cell = []
            self.row.append(self.cell)
        elif tag in BREAK_TAGS and self.cell is not None:
            self.cell.append("\n")

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if tag in ("style", "script"):
            self.skip = max(0, self.skip - 1)
        elif tag in CELL_TAGS:
            self.cell = None
        elif tag == "tr":
            self.row, self.cell = None, None

    def handle_data(self, data):
        if self.cell is not None and not self.skip:
            self.cell.append(data)


def decode(raw):
    for enc in ("utf-8", "cp949"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "ignore")


def tables_of(raw):
    """원문 바이트 → [표[행[칸 글(줄은 '\\n')]]]."""
    p = _Tables()
    p.feed(decode(raw) if isinstance(raw, bytes) else raw)
    p.close()
    out = []
    for t in p.tables:
        rows = []
        for r in t:
            cells = []
            for c in r:
                lines = [re.sub(r"[\s　]+", " ", x).strip() for x in "".join(c).split("\n")]
                cells.append("\n".join(x for x in lines if x))
            if any(cells):
                rows.append(cells)
        if rows:
            out.append(rows)
    return out


def compact(s):
    return re.sub(r"[\s\-–·ㆍ:：\"'“”‘’]+", "", s or "")


SECTION = re.compile(r"^\s*(\d{1,2})\s*[.)]\s*(\S.*)$", re.S)
# 칸 이름은 빈칸 · 줄표를 지운 꼴 **전체**가 [머리(번호 · '계약내역' 등)] + 이름 + [(단위)]여야 함.
# 그래서 '전체계약금액' · '확정계약금액' · '계약상대방최근매출액(원)'(상대 회사 매출) · 설명 문장은 칸 이름이 아님.
PFX = r"(?:\(본문\))?[/?.]*(?:\d{1,2}[.),]?)?(?:(?:계약|해지)(?:내역|내용|금액|기간)|계약기간)?(?:중|의|_|/|>|,|中)?\(?"
SFX = r"(?:\(([^()]*)\))?\)?"
NAMES = (
    ("계약금액총액", r"계약금액총액"),
    ("계약금액", r"계약금액"),
    ("해지금액", r"해지금액"),
    ("최근매출액", r"최근매출액"),
    ("매출액대비%", r"(?:최근)?매출액대비"),
    ("시작일", r"(?:계약)?시작일"),
    ("종료일", r"(?:계약)?종료일"),
    ("상대", r"계약상대(?:방)?"),
)
LABELS = {name: re.compile(PFX + rx + SFX) for name, rx in NAMES}
MAX_LABEL = 30
DATE = re.compile(r"(\d{4})\s*[-./년]\s*(\d{1,2})\s*[-./월]\s*(\d{1,2})\s*일?")
INLINE = re.compile(r"(시작일|종료일)\s*[:：]\s*(\S[^\n]*)")


def label_of(cell):
    """칸 글(한 줄) → (칸 이름, 괄호 단위) 또는 None."""
    if not cell or "\n" in cell.strip():
        return None
    k = compact(cell)
    if not k or len(k) > MAX_LABEL:
        return None
    for name, rx in LABELS.items():
        m = rx.fullmatch(k)
        if m:
            return name, m.group(1)
    return None


def unit_of(paren, table_unit):
    """괄호 단위 → (배수, 이유). 괄호가 없으면 표 '단위' 표기, 그것도 없으면 원으로 봄."""
    u = compact(paren or "") or table_unit
    if not u:
        return 1, None
    if u in UNITS:
        return UNITS[u], None
    if u == "%":
        return None, None
    return None, f"알 수 없는 단위 '{u}'"


def num(cell):
    """칸 글이 숫자 하나일 때만 Decimal. 아니면 (None, 이유). '- 25,767' 처럼 줄표 뒤 빈칸은 글머리표로 보고 뗌."""
    s = (cell or "").strip()
    if not s:
        return None, "빈 칸"
    if "\n" in s:
        return None, "한 칸에 값 여러 줄"
    s = re.sub(r"^[-–·]\s+(?=\d)", "", s)
    flat = re.sub(r"[\s,]", "", s)
    if flat in ("-", "－", "—", "해당없음", "해당사항없음", "미정", "N/A"):
        return None, f"값 없음 '{s[:20]}'"
    m = re.fullmatch(r"(-?\d+(?:\.\d+)?)(?:원|%)?", flat)
    if not m:
        return None, f"숫자 아님 '{s[:30]}'"
    try:
        return Decimal(m.group(1)), None
    except InvalidOperation:
        return None, f"숫자 아님 '{s[:30]}'"


def day(cell, last=False):
    """칸 글의 날짜 → 'YYYY-MM-DD'. 'a ~ b' 범위면 시작일은 a, 종료일(last)은 b."""
    s = (cell or "").strip()
    if not s:
        return None, "빈 칸"
    if "\n" in s:
        s0 = s.split("\n")[0].strip()
        if not DATE.fullmatch(s0):
            return None, "한 칸에 값 여러 줄"
        s = s0
    found = list(DATE.finditer(s))
    if not found:
        return None, f"날짜 아님 '{s[:20]}'"
    if len(found) > 1 and not re.search(r"[~∼～]", s):
        return None, f"날짜 여러 개 '{s[:30]}'"
    m = found[-1] if last else found[0]
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if not (1990 <= y <= 2100 and 1 <= mo <= 12 and 1 <= d <= 31):
        return None, f"날짜 범위 밖 '{s[:20]}'"
    return f"{y:04d}-{mo:02d}-{d:02d}", None


def text(cell):
    s = re.sub(r"\s+", " ", (cell or "")).strip()
    if not s or compact(s) in ("", "-", "해당없음"):
        return None, f"값 없음 '{s[:20]}'"
    return s[:100], None


def table_unit(rows):
    for r in rows:
        for c in r:
            m = re.search(r"단위\s*[:：]?\s*(천\s*원|백만\s*원|억\s*원|원)", c)
            if m:
                return compact(m.group(1))
    return None


def is_fix_header(row):
    k = [compact(c) for c in row]
    return "정정전" in k and "정정후" in k


def value_of(name, cell, paren, tunit):
    """칸 이름별 값 읽기 → (값 문자열, 이유)."""
    if name in ("시작일", "종료일"):
        return day(cell, last=name == "종료일")
    if name == "상대":
        return text(cell)
    v, why = num(cell)
    if v is None:
        return None, why
    if name == "매출액대비%":
        return format(v, "f"), None
    mult, why = unit_of(paren, tunit)
    if mult is None:
        return None, why or "금액 단위가 %"
    if v < 0:
        return None, f"음수 금액 {v}"
    return str(int((v * mult).to_integral_value())), None


def body_candidates(tables):
    """정정사항 표 밖의 표에서 (칸 이름, 값, 이유, 구역)을 문서 순서대로."""
    out, section = [], ""
    for rows in tables:
        if any(is_fix_header(r) for r in rows):
            continue
        tunit = table_unit(rows)
        for r in rows:
            for i, c in enumerate(r):
                m = SECTION.match(c or "")
                if m and i == 0:
                    section = compact(m.group(2))
                for mm in INLINE.finditer(c or ""):
                    v, why = day(mm.group(2), last=mm.group(1) == "종료일")
                    out.append((mm.group(1), v, why, section))
                lab = label_of(c)
                if not lab:
                    continue
                name, paren = lab
                key = "계약금액" if name == "계약금액총액" else name
                if i + 1 >= len(r):
                    out.append((name, None, "옆 칸 없음", section))
                    continue
                v, why = value_of(key, r[i + 1], paren, tunit)
                out.append((name, v, why, section))
    return out


def fix_after(tables):
    """정정사항 표의 정정후 값 → ({칸 이름: (값, 이유)}, 메모, 정정표 있음).

    한 칸에 '2. 계약내역 / 계약금액(원) / 매출액대비(%)'가 쌓이고 옆 칸에 값이 같은 순서로 쌓인 꼴을 줄끼리 맞춤.
    구역 머리 줄('2. 계약내역')은 빼고 맞추며, '3. 계약상대방' 구역 아래 '최근매출액'은 상대 회사 매출이라 버림.
    줄 수가 안 맞으면 그 행은 쓰지 않음(정정전 값을 잘못 잡지 않게)."""
    got, notes, seen = {}, [], False
    for rows in tables:
        head = next((j for j, r in enumerate(rows) if is_fix_header(r)), None)
        if head is None:
            continue
        seen = True
        hk = [compact(c) for c in rows[head]]
        ia, ic = (hk.index("정정항목") if "정정항목" in hk else 0), hk.index("정정후")
        tunit = table_unit(rows)
        for r in rows[head + 1:]:
            if len(r) <= max(ia, ic):
                continue
            raw_items = [x for x in r[ia].split("\n") if x.strip()]
            after = [x for x in r[ic].split("\n") if x.strip()]
            items, sec = [], ""
            for x in raw_items:
                m = SECTION.match(x)
                if m and not label_of(x):
                    sec = compact(m.group(2))
                    continue
                items.append((x, sec))
            if len(items) != len(after):
                if len(raw_items) == len(after):
                    items, sec = [], ""
                    for x in raw_items:
                        m = SECTION.match(x)
                        if m and not label_of(x):
                            sec = compact(m.group(2))
                        items.append((x, sec))
                elif len(items) == 1 and label_of(items[0][0]) and label_of(items[0][0])[0] == "상대" and after:
                    v = re.sub(r"^.*?계약상대방?\s*[:：]\s*", "", after[0])
                    got.setdefault("상대", text(re.sub(r"^[-–·]\s*", "", v)))
                    continue
                else:
                    if any(label_of(x) for x, _ in items):
                        notes.append(f"정정표 줄 수 안 맞음({len(items)}:{len(after)})")
                    continue
            for (it, sec), val in zip(items, after):
                lab = label_of(it)
                if not lab:
                    continue
                name, paren = lab
                if name == "최근매출액" and "계약상대" in sec:
                    continue
                key = "계약금액" if name == "계약금액총액" else name
                v = value_of(key, re.sub(r"^[-–·]\s+(?=\D)", "", val) if key == "상대" else val, paren, tunit)
                if name not in got or (got[name][0] is None and v[0] is not None):
                    got[name] = v
    return got, notes, seen


def pct_ok(p, fields):
    """% 값 검사 → (통과, 이유). 0 ~ 1000 밖이면 계약금액 ÷ 최근매출액 × 100 검산이 맞을 때만 통과."""
    x = Decimal(p)
    a, s = fields.get("계약금액") or fields.get("해지금액"), fields.get("최근매출액")
    calc = Decimal(a) * 100 / Decimal(s) if a and s and Decimal(s) > 0 else None
    agree = calc is not None and abs(calc - x) <= max(Decimal("0.05"), x * Decimal("0.02"))
    if x < 0:
        return False, f"범위 밖(음수 {p})"
    if x > PCT_MAX:
        if agree:
            return True, f"1000% 넘음 · 검산 맞음({calc:.2f})"
        return False, f"범위 밖({p}) · 검산 " + (f"{calc:.2f}" if calc is not None else "불가")
    if calc is not None and not agree and abs(calc - x) > max(Decimal(1), x * Decimal("0.1")):
        return True, f"검산 다름({calc:.2f}) · 값은 둠"
    return True, None


def parse_k2(raw, kind=None):
    """원문 바이트(HTML) → (fields_k2, why_k2). 못 찾은 칸은 None(없음 ≠ 0), 이유는 why_k2에."""
    tables = tables_of(raw)
    cands = body_candidates(tables)
    fields, why = {k: None for k in KEYS}, {}

    def pick(key, names, skip_section=None):
        reasons = []
        for nm in names:
            for name, v, w, sec in cands:
                if name != nm or (skip_section and skip_section in sec):
                    continue
                if v is not None:
                    fields[key] = v
                    return
                reasons.append(w)
        if reasons:
            why[key] = reasons[0]

    pick("계약금액", ["계약금액총액", "계약금액"])
    pick("해지금액", ["해지금액"])
    pick("최근매출액", ["최근매출액"], skip_section="계약상대")
    pick("매출액대비%", ["매출액대비%"])
    pick("시작일", ["시작일"])
    pick("종료일", ["종료일"])
    pick("상대", ["상대"])
    body = dict(fields)

    fix, notes, seen = fix_after(tables)
    amounts = ("계약금액", "최근매출액", "해지금액")
    for name, (v, w) in fix.items():
        key = "계약금액" if name == "계약금액총액" else name
        if v is None or key == "매출액대비%":
            continue
        if fields.get(key) is None:
            fields[key] = v
            why[key] = "본문에 없어 정정후 값"
        elif fields[key] != v:
            if key == "상대":
                why[key] = f"정정후 '{v[:30]}'와 다름 · 본문 값"
            elif key == "최근매출액":
                # 정정표의 '최근 매출액'은 상대 회사 매출(3. 계약상대방 아래)인 경우가 많아 본문을 먼저 씀(원문 대조 2026-10-17)
                why[key] = f"정정후 {v}와 다름 · 본문 값"
            elif key in amounts and any(body.get(o) == v for o in amounts if o != key):
                why[key] = f"정정표 칸 이름 의심(정정후 {v}가 본문 다른 금액과 같음) · 본문 값"
            else:
                why[key] = f"본문({fields[key]})과 정정후 다름 → 정정후"
                fields[key] = v
    # %: 정정후 → 본문 차례로, 범위 검사를 통과하는 첫 값
    tries = []
    fp = fix.get("매출액대비%", (None, None))[0]
    if fp is not None and fp != body.get("매출액대비%"):
        tries.append(("정정후", fp))
    if body.get("매출액대비%") is not None:
        tries.append(("본문", body["매출액대비%"]))
    fields["매출액대비%"] = None
    reasons = []
    for src, p in tries:
        ok, w = pct_ok(p, fields)
        if ok:
            fields["매출액대비%"] = p
            w2 = "; ".join(x for x in reasons + [w] if x)
            if src == "정정후" and body.get("매출액대비%") is not None:
                w2 = "; ".join(x for x in [f"본문({body['매출액대비%']})과 정정후 다름 → 정정후", w2] if x)
            elif src == "정정후":
                w2 = "; ".join(x for x in ["본문에 없어 정정후 값", w2] if x)
            if w2:
                why["매출액대비%"] = w2
            break
        reasons.append(f"{src} {w}")
    else:
        if reasons:
            why["매출액대비%"] = "; ".join(reasons)
    if notes:
        why["정정표"] = notes[0]
    elif kind == "정정" and not seen:
        why["정정표"] = "정정사항 표 못 찾음 · 본문 값"
    for k in KEYS:
        if fields[k] is None and k not in why:
            if k == "해지금액" and kind != "해지":
                continue
            why[k] = "해지 공시(해지금액 칸에 둠)" if k == "계약금액" and kind == "해지" and fields["해지금액"] else "칸 이름 못 찾음"
    return fields, why


def parse_members(members, kind=None):
    """ZIP 안 여러 파일(바이트 목록) → 첫 파일에서 못 찾은 칸만 다음 파일로 채움."""
    fields, why = {k: None for k in KEYS}, {}
    for raw in members:
        f, w = parse_k2(raw, kind)
        for k in KEYS:
            if fields[k] is None and f[k] is not None:
                fields[k] = f[k]
                why.pop(k, None)
                if k in w:
                    why[k] = w[k]
            elif fields[k] is None and k in w and k not in why:
                why[k] = w[k]
        for k, v in w.items():
            if k not in KEYS:
                why.setdefault(k, v)
    return fields, why
