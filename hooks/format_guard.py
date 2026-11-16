#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
생기부 형식 가드 (Format Guard)
- 음슴체(개조식) 종결 여부
- 영역별 글자수 상한
- 금지어(교외수상/어학성적/논문·특허/대학명/부모정보 등) 탐지
- 수식·기호 탐지 — 차단
- 문체 주의어(비유·현학·지어낸 감정)·역량 명시 경고 — 비차단

사용법:
  python format_guard.py --area 과세특 < result.txt
  python format_guard.py --area 진로 --file result.txt
  python format_guard.py --hook   # Claude Code hook(stdin JSON)

종료코드: 위반 있으면 2, 없으면 0. (문체 경고는 종료코드에 영향 없음)
"""
import sys, re, json, argparse

LIMITS = {"과세특": 500, "세특": 500, "교과세특": 500,
          "진로": 700, "진로활동": 700,
          "자율": 500, "자율자치": 500, "자율·자치활동": 500,
          "동아리": 500}

EUMSEUM_END = re.compile(r"(함|음|임|됨|옴|짐|봄|보임|돋보임|인상적임|갖춤|이끎|세움|드러남|키움|넓힘|듦|냄|앎|삼|띔|줌|둠|춤|씀|품|함\.|음\.|임\.)\s*[\.。]?\s*$")
BAD_END = re.compile(r"(했다|한다|된다|이다|입니다|합니다|습니다|였다|봤다|보았다)\s*[\.。]?\s*$")

FORBIDDEN = [
    (r"TOEIC|TOEFL|TEPS|HSK|JLPT|토익|토플|텝스|아이엘츠|IELTS|DELE", "공인 어학시험"),
    (r"모의고사|전국연합|학력평가|백분위|석차|등급(?!제)", "성적/석차 수치"),
    (r"논문|학회지|학술지|특허|발명대회|도서\s?출(간|판)", "논문·특허·출간"),
    (r"[가-힣]+대학교|[가-힣]{2,}대(?=\s|에|에서|입학|진학)|서울대|연세대|고려대", "특정 대학명"),
    (r"학원|과외|인강|강사", "사교육·강사"),
    (r"아버지|어머니|부모님?\s*(직업|회사|대표|교수|의사|변호사)", "부모 정보"),
    (r"해외\s?(연수|봉사|캠프)|어학연수", "해외 활동"),
]

# 수식·기호(차단): 수학·과학 세특에 수식을 그대로 쓰지 않는다.
FORMULA = [
    (r"[A-Za-z]\s*\(\s*[A-Za-z0-9]+\s*\)\s*=", "함수식 f(x)=…"),
    (r"(?<![A-Za-z])[a-zA-Z]\s*=\s*[-0-9(a-zA-Z]", "등식 y=…"),
    (r"[A-Za-z0-9)]\s*[²³⁴]|\^", "거듭제곱 기호"),
    (r"[∑∫√π∞≤≥≠±]", "수학 기호"),
    (r"\d\s*[×÷]\s*\d|\d\s*/\s*\d+\s*[A-Za-z]", "계산식"),
]

# 역량 명시(비차단 경고): 역량 이름 대신 수업 장면으로.
COMPETENCY_WARN = [
    r"(문제\s?해결|수학적\s?사고|논리적\s?사고|비판적\s?사고|창의적\s?사고)(력|능력)",
    r"(탐구|학업|공동체|진로)\s?역량",
    r"(힘|감각|능력|역량)을\s*(고르게\s*)?보임",
    r"(힘|감각|능력|역량)이\s*(돋보임|뛰어남|우수함)",
]

# 문체 주의어(비차단 경고): 비유·현학 표현과 지어낸 감정·의욕 서술.
STYLE_WARN = [
    (r"밀고 나가", "비유·현학 표현"),
    (r"함께 바라", "비유·현학 표현"),
    (r"촘촘히 잇", "비유·현학 표현"),
    (r"선을 긋는", "비유·현학 표현"),
    (r"의미를 세우", "비유·현학 표현"),
    (r"두 자리에서", "비유·현학 표현"),
    (r"눈으로 뜯어", "비유·현학 표현"),
    (r"하고 싶어\s*함", "지어낸 의욕 서술"),
    (r"흥미로워함", "지어낸 감정 서술"),
    (r"받아들임", "지어낸 감정 서술"),
    (r"마음을 품", "지어낸 감정 서술"),
    (r"눈을 반짝", "지어낸 감정 서술"),
]


def ends_with_mieum(s: str) -> bool:
    """음슴체 명사형 종결(받침 ㅁ: 올림·드묾·띔 등)이면 True."""
    s = re.sub(r"[\s\.。”\"')）]+$", "", s)
    if not s:
        return False
    c = ord(s[-1])
    return 0xAC00 <= c <= 0xD7A3 and (c - 0xAC00) % 28 in (16, 10)  # ㅁ, ㄻ


def count_korean_chars(text: str) -> int:
    return len(text.replace("\n", "").replace("\r", ""))


def split_sentences(text: str):
    parts = re.split(r"(?<=[\.。])\s+|\n+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def check(text: str, area: str):
    issues = []
    limit = LIMITS.get(area.replace(" ", ""), None)
    n = count_korean_chars(text)
    if limit and n > limit:
        issues.append(f"글자수 초과: {n}자 / 상한 {limit}자")
    bad_sents = []
    for s in split_sentences(text):
        core = s.rstrip("”\"')）)")
        if BAD_END.search(core) or not (EUMSEUM_END.search(core) or ends_with_mieum(core)):
            bad_sents.append(s[:30])
    if bad_sents:
        issues.append("음슴체 위반 의심 문장: " + " / ".join(bad_sents[:5]))
    for pat, label in FORBIDDEN:
        if re.search(pat, text):
            issues.append(f"금지어 탐지({label}): /{pat}/")
    for pat, label in FORMULA:
        m = re.search(pat, text)
        if m:
            issues.append(f"수식 탐지({label}): '{m.group(0)}' → 말로 풀어 쓰기")
    warns = []
    for pat in COMPETENCY_WARN:
        m = re.search(pat, text)
        if m:
            warns.append(f"역량 명시: '{m.group(0)}' → 수업 장면으로")
    for pat, label in STYLE_WARN:
        m = re.search(pat, text)
        if m:
            warns.append(f"{label}: '{m.group(0)}'")
    return n, limit, issues, warns


def extract_text_from_hook(stdin_data: str):
    try:
        obj = json.loads(stdin_data)
    except Exception:
        return stdin_data
    for k in ("response", "text", "content", "message", "tool_input"):
        v = obj.get(k)
        if isinstance(v, str) and v.strip():
            return v
        if isinstance(v, dict):
            for kk in ("content", "new_string", "text"):
                if isinstance(v.get(kk), str):
                    return v[kk]
    return stdin_data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--area", default="과세특")
    ap.add_argument("--file")
    ap.add_argument("--hook", action="store_true")
    args = ap.parse_args()

    if args.file:
        with open(args.file, encoding="utf-8") as f:
            text = f.read()
    else:
        raw = sys.stdin.read()
        text = extract_text_from_hook(raw) if args.hook else raw

    n, limit, issues, warns = check(text, args.area)

    if args.hook:
        if warns:
            sys.stderr.write("문체 주의(경고, 비차단): " + " | ".join(warns) + "\n")
        if issues:
            print(json.dumps({"decision": "block",
                              "reason": "생기부 형식 가드 위반: " + " | ".join(issues)},
                             ensure_ascii=False))
        sys.exit(2 if issues else 0)

    print(f"영역: {args.area} | 글자수: {n}자" + (f" / 상한 {limit}자" if limit else ""))
    if warns:
        print("⚠️ 문체 주의(경고, 비차단 — 비유·현학·지어낸 감정):")
        for w in warns:
            print("  -", w)
    if not issues:
        print("✅ 통과: 음슴체/글자수/금지어 문제 없음" + (" (문체 경고는 위 참고)" if warns else ""))
        sys.exit(0)
    print("⚠️ 점검 필요:")
    for i in issues:
        print("  -", i)
    sys.exit(2)


if __name__ == "__main__":
    main()
