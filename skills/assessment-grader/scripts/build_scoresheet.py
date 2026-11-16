#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
수행평가 채점 결과 → 표준 엑셀 워크북 생성기.

입력: 채점 결과 JSON (references/excel-output.md 스키마)
출력: 3개 시트(.xlsx)
  1) 채점결과 (기준별 점수 분해)
  2) 근거·피드백
  3) 요약 통계

사용법:
  pip install --break-system-packages openpyxl
  python build_scoresheet.py grades.json -o 결과.xlsx
  cat grades.json | python build_scoresheet.py -          # stdin

설계 원칙:
  - 총점은 입력값을 신뢰하지 않고 요소 점수로 재계산·검산한다.
  - 요소 점수 > 만점이면 경고를 표시한다(점수는 보존, 사람이 검토).
"""
import sys, json, argparse, statistics, datetime

try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    from openpyxl.utils import get_column_letter
    from openpyxl.chart import BarChart, Reference
except ImportError:
    sys.stderr.write("openpyxl 필요: pip install --break-system-packages openpyxl\n")
    raise

HEADER_FILL = PatternFill("solid", fgColor="305496")
HEADER_FONT = Font(bold=True, color="FFFFFF")
TOTAL_FILL = PatternFill("solid", fgColor="FFF2CC")
FLAG_FILL = PatternFill("solid", fgColor="FCE4D6")
THIN = Side(style="thin", color="BFBFBF")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
WRAP_TOP = Alignment(wrap_text=True, vertical="top")
CENTER = Alignment(horizontal="center", vertical="center")


def load(path):
    raw = sys.stdin.read() if path == "-" else open(path, encoding="utf-8").read()
    return json.loads(raw)


def compute_total(stu, criteria):
    """요소 점수 가중 합. 가중치는 criteria의 weight(없으면 1)."""
    total = 0.0
    for c in criteria:
        w = c.get("weight", 1) or 1
        v = stu.get("scores", {}).get(c["name"])
        if isinstance(v, (int, float)):
            total += v * w
    return round(total, 2)


def style_header(ws, row=1):
    for cell in ws[row]:
        if cell.value is not None:
            cell.fill = HEADER_FILL
            cell.font = HEADER_FONT
            cell.alignment = CENTER
            cell.border = BORDER


def autosize(ws, max_w=60):
    for col in ws.columns:
        length = 0
        letter = get_column_letter(col[0].column)
        for cell in col:
            if cell.value is not None:
                # 한글 폭 보정
                s = str(cell.value)
                w = sum(2 if ord(ch) > 0x1100 else 1 for ch in s)
                length = max(length, w)
        ws.column_dimensions[letter].width = min(max(length + 2, 8), max_w)


def warnings_for(data):
    warns = []
    crit = {c["name"]: c for c in data["criteria"]}
    declared_total = data.get("total")
    crit_sum = sum((c.get("max", 0) * (c.get("weight", 1) or 1)) for c in data["criteria"])
    if declared_total is not None and round(crit_sum, 2) != round(declared_total, 2):
        warns.append(f"기준표 총점({declared_total}) ≠ 요소 만점 합({crit_sum})")
    for stu in data["students"]:
        for c in data["criteria"]:
            v = stu.get("scores", {}).get(c["name"])
            if isinstance(v, (int, float)) and v > c.get("max", 0):
                warns.append(f"{stu.get('name')} · {c['name']}: 점수 {v} > 만점 {c['max']}")
    return warns


def sheet_scores(wb, data):
    ws = wb.active
    ws.title = "채점결과"
    crit = data["criteria"]
    header = ["학번", "이름"] + [f"{c['name']} /{c['max']}" for c in crit] + \
             [f"총점 /{data.get('total','')}", "등급", "확인필요"]
    ws.append(header)
    for stu in data["students"]:
        total = compute_total(stu, crit)
        row = [stu.get("id", ""), stu.get("name", "")]
        for c in crit:
            row.append(stu.get("scores", {}).get(c["name"], ""))
        row += [total, stu.get("grade", ""), stu.get("flag", "") or stu.get("status", "")]
        ws.append(row)
    style_header(ws)
    ws.freeze_panes = "A2"
    total_col = 2 + len(crit) + 1  # 총점 열 index(1-based)
    flag_col = total_col + 2
    for r in range(2, ws.max_row + 1):
        for c in range(1, ws.max_column + 1):
            ws.cell(r, c).border = BORDER
            if c > 2:
                ws.cell(r, c).alignment = CENTER
        ws.cell(r, total_col).fill = TOTAL_FILL
        ws.cell(r, total_col).font = Font(bold=True)
        fv = ws.cell(r, flag_col).value
        if fv and fv not in ("제출", ""):
            ws.cell(r, flag_col).fill = FLAG_FILL
    autosize(ws, max_w=18)


def sheet_feedback(wb, data):
    ws = wb.create_sheet("근거·피드백")
    ws.append(["이름", "평가요소", "부여점수/만점", "근거", "피드백"])
    for stu in data["students"]:
        name = stu.get("name", "")
        for c in data["criteria"]:
            cn = c["name"]
            sc = stu.get("scores", {}).get(cn, "")
            ev = stu.get("evidence", {}).get(cn, "")
            fb = stu.get("feedback", {}).get(cn, "")
            ws.append([name, cn, f"{sc}/{c['max']}", ev, fb])
    style_header(ws)
    ws.freeze_panes = "A2"
    ws.column_dimensions["A"].width = 12
    ws.column_dimensions["B"].width = 16
    ws.column_dimensions["C"].width = 12
    ws.column_dimensions["D"].width = 55
    ws.column_dimensions["E"].width = 55
    for r in range(2, ws.max_row + 1):
        for c in range(1, 6):
            cell = ws.cell(r, c)
            cell.border = BORDER
            cell.alignment = WRAP_TOP if c in (4, 5) else CENTER


def sheet_summary(wb, data):
    ws = wb.create_sheet("요약 통계")
    crit = data["criteria"]
    submitted = [s for s in data["students"] if (s.get("status", "제출") == "제출")]
    totals = [compute_total(s, crit) for s in submitted]
    n_all = len(data["students"])
    n_sub = len(submitted)
    n_miss = sum(1 for s in data["students"] if s.get("status") == "미제출")
    n_chk = sum(1 for s in data["students"] if s.get("status") == "확인필요" or s.get("flag"))

    ws.append(["항목", "값"])
    rows = [
        ("과제명", data.get("assignment", "")),
        ("채점일", data.get("date", datetime.date.today().isoformat())),
        ("총점(만점)", data.get("total", "")),
        ("전체 인원", n_all),
        ("제출", n_sub),
        ("미제출", n_miss),
        ("확인필요/플래그", n_chk),
    ]
    if totals:
        rows += [
            ("총점 평균", round(statistics.mean(totals), 2)),
            ("총점 최고", max(totals)),
            ("총점 최저", min(totals)),
            ("총점 중앙값", round(statistics.median(totals), 2)),
            ("총점 표준편차", round(statistics.pstdev(totals), 2) if len(totals) > 1 else 0),
        ]
    for r in rows:
        ws.append(list(r))

    # 요소별 평균
    ws.append([])
    head_row = ws.max_row + 1
    ws.append(["평가요소", "만점", "평균 점수", "평균 달성률"])
    for c in crit:
        vals = [s.get("scores", {}).get(c["name"]) for s in submitted]
        vals = [v for v in vals if isinstance(v, (int, float))]
        avg = round(statistics.mean(vals), 2) if vals else 0
        rate = f"{round(100*avg/c['max'])}%" if c.get("max") else ""
        ws.append([c["name"], c["max"], avg, rate])

    # 점수 분포(총점 기준 구간)
    dist_head = None
    if totals and data.get("total"):
        ws.append([])
        dist_head = ws.max_row + 1
        ws.append(["점수 구간", "인원"])
        T = data["total"]
        bins = [("90-100%", 0.9, 1.01), ("80-89%", 0.8, 0.9), ("70-79%", 0.7, 0.8),
                ("60-69%", 0.6, 0.7), ("60% 미만", -0.01, 0.6)]
        for label, lo, hi in bins:
            cnt = sum(1 for t in totals if lo <= (t / T) < hi)
            ws.append([label, cnt])
        # 막대 차트
        chart = BarChart()
        chart.title = "총점 분포"
        chart.type = "col"
        chart.legend = None
        data_ref = Reference(ws, min_col=2, min_row=dist_head, max_row=dist_head + len(bins))
        cats = Reference(ws, min_col=1, min_row=dist_head + 1, max_row=dist_head + len(bins))
        chart.add_data(data_ref, titles_from_data=True)
        chart.set_categories(cats)
        ws.add_chart(chart, "E2")

    style_header(ws)
    style_header(ws, head_row)
    if dist_head:
        style_header(ws, dist_head)
    ws.column_dimensions["A"].width = 18
    ws.column_dimensions["B"].width = 14
    ws.column_dimensions["C"].width = 14
    ws.column_dimensions["D"].width = 14

    # 경고 표기
    warns = warnings_for(data)
    if warns:
        ws.append([])
        ws.append(["⚠ 검증 경고"])
        ws.cell(ws.max_row, 1).font = Font(bold=True, color="C00000")
        for w in warns:
            ws.append([w])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", help="채점 JSON 경로 또는 '-'(stdin)")
    ap.add_argument("-o", "--output", help="출력 xlsx 경로")
    args = ap.parse_args()

    data = load(args.input)
    for key in ("criteria", "students"):
        if key not in data:
            sys.exit(f"JSON에 '{key}' 누락")

    wb = Workbook()
    sheet_scores(wb, data)
    sheet_feedback(wb, data)
    sheet_summary(wb, data)

    out = args.output
    if not out:
        assign = data.get("assignment", "수행평가").replace(" ", "")
        d = data.get("date", datetime.date.today().isoformat()).replace("-", "")
        out = f"수행평가_채점결과_{assign}_{d}.xlsx"
    wb.save(out)

    warns = warnings_for(data)
    print(f"✅ 저장: {out}")
    if warns:
        print("⚠ 검증 경고:")
        for w in warns:
            print("  -", w)


if __name__ == "__main__":
    main()
