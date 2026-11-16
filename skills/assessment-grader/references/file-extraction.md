# 제출물·파일 분석 (모든 형식)

목표: Classroom/Drive 및 직접 업로드된 어떤 형식이든 내용을 추출해 **채점 근거**로 쓴다. 못 읽으면 추측하지 말고 알린다.

## 1. Google Classroom
- 교사가 수업(클래스)·과제명을 주면, 연결된 Classroom 도구로 해당 과제의 **학생 제출물 목록**과 첨부를 수집.
- 첨부가 Drive 파일이면 Drive 도구로 내용 읽기.
- 학생 식별: 제출자 이름/이메일 → 교사 명단과 매핑. 모호하면 1회 확인.
- 미제출자도 목록에 포함해 '미제출' 표시.

## 2. Google Drive
- 과제 폴더/파일명/학생명으로 검색 후 내용 읽기.
- Google Docs/Sheets/Slides는 텍스트·표·슬라이드 내용으로 추출.

## 3. 업로드 파일 형식별 처리
- **Word (.docx)**: docx 스킬로 본문·표 추출.
- **PDF**: pdf 스킬로 텍스트·표 추출. 스캔 PDF는 OCR.
- **PPT (.pptx)**: pptx 스킬로 슬라이드 텍스트·노트 추출.
- **텍스트/CSV/엑셀**: 직접 읽기.
- **이미지 (.png/.jpg/.jpeg)**: 사진/스캔/손글씨 답안 → 이미지를 직접 보고 내용 판독. 표·도식·수식 포함. 불확실 부분은 '확인 필요' 표시.

## 4. 한글 파일 (.hwp / .hwpx) — 국내 학교 필수
한글 파일은 바로 못 읽는 경우가 많으므로 단계적으로 처리한다.

1. **.hwpx 우선 시도**: hwpx는 ZIP+XML 구조다. 압축 해제 후 `Contents/section*.xml`의 텍스트를 추출할 수 있다.
   ```bash
   # 예: 텍스트 대략 추출 (정밀 추출은 전용 변환기 권장)
   unzip -o "제출물.hwpx" -d _hwpx_tmp
   # section XML에서 텍스트 노드 추출 (간이)
   python3 - <<'PY'
   import glob, re, html
   text = []
   for f in glob.glob('_hwpx_tmp/Contents/section*.xml'):
       s = open(f, encoding='utf-8', errors='ignore').read()
       for m in re.findall(r'<hp:t[^>]*>(.*?)</hp:t>', s, re.S):
           text.append(html.unescape(re.sub(r'<[^>]+>', '', m)))
   print('\n'.join(text))
   PY
   ```
2. **.hwp(구형 바이너리)**: 가능하면 변환 도구 사용.
   - `hwp5txt`(pyhwp): `pip install --break-system-packages pyhwp` 후 `hwp5txt 파일.hwp`
   - 또는 LibreOffice 헤드리스 변환: `libreoffice --headless --convert-to pdf 파일.hwp` 후 PDF 추출.
   - 설치/변환 도구가 없으면 시도 후 결과를 검증.
3. **모두 실패 시**: 추측 채점 금지. 교사에게 **PDF 또는 워드/텍스트로 변환본**을 요청하거나, 한글에서 '다른 이름으로 저장 → PDF'를 안내.

> hwp 자동 추출은 서식·표가 깨질 수 있으니, 추출 텍스트가 부실하면 채점 전에 교사에게 확인한다.

## 5. 공통 원칙
- 추출 내용은 **채점 근거**로만 사용. 결과물에 원문을 길게 복붙하지 않음(짧은 인용만).
- 개인정보(연락처·주소 등)는 결과에 노출하지 않음.
- 학생-제출물 매핑을 표로 정리해 두고, 누락/중복/판독불가를 명확히 표시.
- 추출 실패 항목은 채점에서 빼지 말고 '확인 필요'로 남겨 교사가 처리하게 한다.
