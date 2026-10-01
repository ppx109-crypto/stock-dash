import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import collect_daily as C

TODAY = date(2026, 10, 1)


class FakeDart:
    """시장 공시 목록만 흉내 냄. 처음부터 받기는 collect를 바꿔 끼워 셈."""

    def __init__(self, rows):
        self.rows, self.calls = rows, []

    def dart(self, endpoint, **params):
        self.calls.append(params.get("page_no"))
        page = params["page_no"]
        return {"list": self.rows[(page - 1) * 2: page * 2], "total_page": max(1, (len(self.rows) + 1) // 2)}

    def corp(self, code):
        return "corp"

    def business_excerpt(self, receipt):
        return "새 원문"


def row(code, day, name, no):
    return {"stock_code": code, "rcept_dt": day, "report_nm": name, "rcept_no": no}


class DailyDart(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.mkdtemp())
        for target, value in ((C, "FOLDER"),):
            p = patch.object(target, value, self.folder)
            p.start()
            self.addCleanup(p.stop)
        self.full = []
        p = patch.object(C, "collect", lambda code, shared: self.full.append(code) or
                         {"code": code, "since": C.FIRST_YEAR_DEFAULT, "years": [{"receipt": "R1"}],
                          "fetched": TODAY.isoformat(), "disclosures": []})
        p.start()
        self.addCleanup(p.stop)

    def write(self, code, fetched="2026-09-29", **more):
        body = {"code": code, "since": C.FIRST_YEAR_DEFAULT, "fetched": fetched, "years": [{"receipt": "R1"}],
                "business_excerpt": "옛 원문", "disclosures": [
                    {"title": "옛 공시", "date": "20260920", "url": "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=1"},
                    {"title": "아주 옛 공시", "date": "20260501", "url": "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=0"}], **more}
        (self.folder / f"{code}.json").write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")

    def read(self, code):
        return json.loads((self.folder / f"{code}.json").read_text(encoding="utf-8"))

    def test_only_new_notices_are_added_without_full_download(self):
        self.write("000010")
        fake = FakeDart([row("000010", "20260930", "단일판매ㆍ공급계약체결", "5"), row("", "20260930", "펀드", "6"),
                         row("000099", "20260930", "주요사항보고서", "7")])
        C.run(["000010"], shared=fake, today=TODAY)
        got = self.read("000010")
        self.assertEqual(self.full, [])
        self.assertEqual([d["title"] for d in got["disclosures"]], ["단일판매ㆍ공급계약체결", "옛 공시"], "90일 넘은 것은 뺌")
        self.assertEqual(got["fetched"], TODAY.isoformat())
        self.assertEqual(len(fake.calls), 2, "100줄씩 끝 쪽까지 넘겨 받음")

    def test_periodic_report_or_missing_file_downloads_again(self):
        self.write("000010")
        fake = FakeDart([row("000010", "20260930", "[기재정정]반기보고서 (2026.06)", "5")])
        C.run(["000010", "000020"], shared=fake, today=TODAY)
        self.assertEqual(sorted(self.full), ["000010", "000020"])
        self.assertEqual(self.read("000010")["business_excerpt"], "옛 원문", "마지막 결산 접수번호가 같으면 원문은 다시 받지 않음")

    def test_rotation_and_old_files(self):
        k = C.needs_full
        self.assertEqual(k("000010", None, [], TODAY), "파일 없음")
        self.assertEqual(k("000010", {"since": C.FIRST_YEAR_DEFAULT, "fetched": "2026-06-01"}, [], TODAY), "오래됨")
        code = next(f"{n:06d}" for n in range(1, 100) if n % C.ROTATE == TODAY.toordinal() % C.ROTATE)
        self.assertEqual(k(code, {"since": C.FIRST_YEAR_DEFAULT, "fetched": "2026-09-30"}, [], TODAY), "돌아가며 다시 받기")

    def test_deadline_leaves_rest_for_tomorrow(self):
        with patch.object(C, "DEADLINE_MIN", 0):
            C.run(["000010", "000020"], shared=FakeDart([]), today=TODAY)
        self.assertEqual(self.full, [])


if __name__ == "__main__":
    unittest.main()
