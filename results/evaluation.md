# 종합실습 평가 기록

## 현재 상태

2026-10-02: 구현과 무과금 로컬 검증 완료. **실제 RAG 성능 평가는 미실행**이다. 수집 대상 키워드 답변과 `.env`의 OPENAI_API_KEY가 필요하다. 평가하지 않은 수치와 개선 효과는 기록하지 않는다.

## 확인한 사실

- 작업 디렉토리 retrivr-assistant, origin bashdas/retrivr-assistant 확인. 시작 시 작업 트리 깨끗함, 적용 AGENTS.md 없음.
- Python 3.11.15, 기존 pyproject.toml 의존성 설치 및 CLI 실행 확인.
- Swagger `/v3/api-docs` HTTP 200. 인증 헤더 없이 단체 검색, 단체 1의 물품 목록, 물품 1 상세 모두 HTTP 200 확인.
- Swagger 예시 검색 키워드는 빈 결과였다. 이는 해당 조회의 결과일 뿐 다른 단체나 전체 물품이 없다는 의미가 아니다.
- 인증 확인용 응답은 평가 데이터셋으로 사용하지 않았다.
- 가상 fixture 기반 테스트 3개 통과: 중복 제거·페이지네이션·실패 보존·긴 청크 식별 정보, 커서 타입/반복 감지, 실패 목록을 빈 재고로 오인하지 않음.

## 비교 조건

| 항목 | 설정 |
|---|---|
| 실제 스냅샷/고정 질문 | 키워드 수신 후 생성 및 검토 예정 |
| Splitter | 본문 900자 / 중복 150자, 식별 헤더 복원 |
| Embedding | text-embedding-3-small |
| Vector Store / Top-K | FAISS / 3 |
| Baseline | similarity |
| 개선 후보 | BM25 + vector RRF, 상수 60 |
| Generation | gpt-4o-mini, temperature 0 |

## 질문별 결과

실제 데이터에서 `--mode prepare`로 10개 질문과 정답 문서 ID/근거를 고정한다. 고정 질문 파일이 아직 없으므로 평가 질문 확정도 미완료이다. 질문별 Top-K 원문·출처·Hit·답변은 run JSON에 저장되며, 실행 후 아래 항목을 실제 관찰로 채운다.

| 항목 | Baseline | Hybrid |
|---|---|---|
| Retrieval Hit Rate | 미측정 | 미측정 |
| 근거 일치 | 미평가 | 미평가 |
| 질문에 직접 응답 | 미평가 | 미평가 |
| 무근거 질문 답변 제한 | 미평가 | 미평가 |

## 개선 근거와 남은 작업

관찰한 Baseline 실패: 아직 없음(미실행). Hybrid는 이름/ID와 자연어 의미 검색을 결합하는 후보로만 구현했다. 효과가 같거나 나빠져도 그대로 기록해야 한다.

1. 키워드로 실제 스냅샷을 수집하고 manifest.errors 및 목록 완료 여부를 확인한다.
2. 10개 질문과 정답 근거를 검토·고정한다. 문서에 답이 없는 질문은 Hit Rate에서 제외한다.
3. plan으로 호출 규모를 확인하고 Baseline Retrieval/Generation을 실행한다.
4. 검색 원문과 답변에서 실패 원인을 기록한 뒤 같은 데이터·질문으로 compare를 실행한다.
5. generation_review를 수동 판정하고, 질문별 좋아짐/동일/나빠짐과 근거를 이 문서에 기록한다.

가상 테스트 통과를 실제 검색 품질 또는 생성 품질의 개선 증거로 사용하지 않는다.
