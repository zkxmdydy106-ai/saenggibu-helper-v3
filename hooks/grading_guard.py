#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
채점 가드 (Grading Guard)
채점 결과 JSON이 채점기준표 규칙을 지키는지 검증한다.

검사 항목:
  1) 채점기준표 존재 (criteria 비어있지 않음)
  2) 요소 점수 ≤ 해당 요소 만점 (음수 금지)
  3) 모든 제출 학생이 모든 요소에 점수 보유 (누락 탐지)
  4) 총점 = 요소 점수 가중 합, 그리고 ≤ 기준표 총점
  5) 모든 점수에 근거(evidence) 존재
  6) 기준표 총점 == 요소 만점(가중) 합

사용법:
  # 단독 점검
  python grading_guard.py --file grades.json

  # Claude Code hook(Stop/PostToolUse): stdin으로 hook JSON 또는 채점 JSON
  python grading_guard.py --hook < payload.json

종료코드: 위반 있으면 2, 없으면 0.
"""
import sys, json, argparse


def find_grading_json(obj):
    """hook 페이로드 안에서 채점 JSON(dict with criteria/students)을 찾는다."""
    if isinstance(obj, dict):
        if "criteria" in obj and "students" in obj:
            return obj
        for v in obj.values():
            r = find_grading_json(v)
            if r:
                return r
            if isinstance(v, str):
                try:
                    r = find_grading_json(json.loads(v))
                    if r:
                        return r
                except Exception:
                    pass
    elif isinstance(obj, list):
        for v in obj:
            r = find_grading_json(v)
            if r:
                return r
    return None


def check(data):
    issues = []
    crit = data.get("criteria") or []
    students = data.get("students") or []

    if not crit:
        issues.append("채점기준표(criteria)가 없음 — 기준 없이 채점 불가")
        return issues

    # 6) 기준표 총점 == 요소 만점 합
    crit_sum = sum((c.get("max", 0) * (c.get("weight", 1) or 1)) for c in crit)
    declared = data.get("total")
    if declared is not None and round(crit_sum, 2) != round(declared, 2):
        issues.append(f"기준표 총점({declared}) ≠ 요소 만점 합({crit_sum})")

    maxmap = {c["name"]: c for c in crit}

    for stu in students:
        name = stu.get("name") or stu.get("id") or "?"
        status = stu.get("status", "제출")
        if status in ("미제출",):
            continue  # 미제출은 점수 검사 제외
        scores = stu.get("scores", {})
        evid = stu.get("evidence", {})

        for c in crit:
            cn = c["name"]
            v = scores.get(cn)
            # 3) 누락
            if v is None or v == "":
                if status != "확인필요":
                    issues.append(f"[{name}] '{cn}' 점수 누락")
                continue
            if not isinstance(v, (int, float)):
                issues.append(f"[{name}] '{cn}' 점수가 숫자 아님: {v!r}")
                continue
            # 2) 만점 초과/음수
            mx = c.get("max", 0)
            if v > mx:
                issues.append(f"[{name}] '{cn}' 점수 {v} > 만점 {mx}")
            if v < 0:
                issues.append(f"[{name}] '{cn}' 점수 음수: {v}")
            # 5) 근거
            if not (evid.get(cn) and str(evid.get(cn)).strip()):
                issues.append(f"[{name}] '{cn}' 근거(evidence) 없음")

        # 4) 총점 검산
        calc = sum((scores.get(c["name"], 0) or 0) * (c.get("weight", 1) or 1)
                   for c in crit if isinstance(scores.get(c["name"]), (int, float)))
        calc = round(calc, 2)
        if declared is not None and calc > declared + 1e-9:
            issues.append(f"[{name}] 총점 {calc} > 기준표 총점 {declared}")
        rep = stu.get("total")
        if isinstance(rep, (int, float)) and round(rep, 2) != calc:
            issues.append(f"[{name}] 보고 총점 {rep} ≠ 계산 총점 {calc}")

    return issues


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file")
    ap.add_argument("--hook", action="store_true")
    args = ap.parse_args()

    raw = open(args.file, encoding="utf-8").read() if args.file else sys.stdin.read()
    try:
        obj = json.loads(raw)
    except Exception as e:
        msg = f"채점 JSON 파싱 실패: {e}"
        if args.hook:
            print(json.dumps({"decision": "block", "reason": msg}, ensure_ascii=False))
            sys.exit(2)
        print(msg); sys.exit(2)

    data = find_grading_json(obj) if args.hook else obj
    if not data:
        # hook 모드인데 채점 JSON이 없으면 통과(다른 작업)
        if args.hook:
            sys.exit(0)
        print("채점 JSON 구조 아님"); sys.exit(2)

    issues = check(data)

    if args.hook:
        if issues:
            print(json.dumps({"decision": "block",
                              "reason": "채점 가드 위반: " + " | ".join(issues[:10])},
                             ensure_ascii=False))
        sys.exit(2 if issues else 0)

    if not issues:
        print("✅ 통과: 만점·합계·근거·누락 문제 없음")
        sys.exit(0)
    print("⚠️ 채점 가드 위반:")
    for i in issues:
        print("  -", i)
    sys.exit(2)


if __name__ == "__main__":
    main()
