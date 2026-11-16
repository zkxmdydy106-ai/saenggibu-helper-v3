# HOOK_채점가드 — grading_guard.py

채점 결과가 채점기준표 규칙을 어기지 않는지 **출력 직전 자동 검증**하는 가드.

## 무엇을 막나
- 채점기준표 없이 산출된 결과
- 요소 점수가 만점 초과 / 음수
- 일부 학생·요소 점수 누락
- 총점 산술 오류(요소 합 불일치, 기준표 총점 초과)
- 점수에 근거(evidence) 누락
- 기준표 총점 ≠ 요소 만점 합

## 단독 사용
```bash
python hooks/grading_guard.py --file grades.json
```
위반 시 종료코드 2 + 위반 목록 출력. 0이면 통과.

## Claude Code hook 등록 (선택)
`.claude/settings.json`에 Stop/PostToolUse 훅으로 등록하면, 채점 JSON을 산출할 때 자동 검증 후 위반 시 차단된다.

```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "python \"$CLAUDE_PROJECT_DIR/수행평가채점기/hooks/grading_guard.py\" --hook"
          }
        ]
      }
    ]
  }
}
```

- `--hook` 모드는 stdin의 hook 페이로드 안에서 채점 JSON(`criteria`+`students`)을 자동 탐색한다.
- 채점 JSON이 없는 일반 작업이면 통과(exit 0)한다.
- 위반 시 `{"decision":"block","reason":...}` 출력 + exit 2.

## 환경별
- **Claude 웹/앱 Project**: 훅 자동 실행은 안 되지만, 프로젝트지침 §7 자가 점검이 동일 효과. 필요하면 산출 JSON을 이 스크립트로 수동 점검.
- **Claude Code**: 위 settings 스니펫을 `.claude/settings.json`에 병합, `grading_guard.py`를 repo에 둔다.

## 채점 JSON 스키마
`skills/assessment-grader/references/excel-output.md` 참고. `build_scoresheet.py`와 동일 스키마를 공유하므로, **같은 JSON으로 검증 → 엑셀 생성**의 파이프라인이 된다.
