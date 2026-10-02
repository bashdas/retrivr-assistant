# Retrivr Assistant 설계 및 데이터 사용 내역

## 1. 문제 정의와 구현 범위

학교·학과·단체명을 알고 있는 사용자가 해당 단체의 물품 목록, 대여 가능 수량, 개별 상태와 대여 조건을 자연어로 확인하도록 돕는다. 사용자 소속 조회 API가 없으므로 소속을 추정하지 않고 사용자가 제공한 키워드를 검색 범위로 삼는다.

초기 구현은 질문마다 API를 호출하는 에이전트가 아닌 **수집 시점의 정보를 검색하는 스냅샷 RAG**다. 수집 키워드 밖의 단체, 미래/현재 실시간 수량, 사용자 본인의 소속이나 대여 자격은 확인할 수 없다. 예약·대여 신청·개인정보 조회·관리자 변경 API는 사용하지 않는다. 현재 산출물은 수집 및 평가용 CLI이며 웹 챗봇 배포는 범위에 포함하지 않는다.

## 2. 데이터 범위와 사용 내역

평가는 구현 코드·설계·평가 결과를 중심으로 한다는 안내에 따라 **`data/`는 제출 필수 항목에서 제외할 수 있다.** 원본 데이터 폴더를 제외하더라도 사용 범위와 실험 목적을 확인할 수 있도록 데이터 내역을 기록했다.

| 구분 | 출처/범위 | 규모 | 사용 목적 | 상태 |
|---|---|---|---|---|
| 강의 샘플 | `data/sample.txt`, `data/sample.pdf` | 기존 스켈레톤 자료 | 기존 강의 예제용 | 서비스 주 평가에는 미사용 |
| EC2 테스트 서버 | 검색 키워드 `리트리버`, 단체 ID 1 | 물품 3종, 문서 4개 | 최초 API 연결·수집 및 RAG 시험 | 주 실험과 분리 |
| 가상 MOCK | 생성기 `src/create_mock_data.py`, 키워드 `가상누리대학교`, `가상한빛대학교` | 단체 5개, 물품 24종, 문서/청크 29개 | Baseline·Hybrid·생성 개선 비교 | 주 비교 실험 완료 |
| 운영 서버 | `https://www.retrivr.kr`, 키워드 `건국대학교`, `리트리버` | 단체 4개, 물품 11종, 문서 15개, 청크 17개 | 실제 수집→검색→생성의 최종 실행 확인 | 수집·검색·개선 생성 완료 |

운영 수집은 2026-10-02 10:47경 KST에 수행했다. 최종 스냅샷은 `data/snapshots/production-validation`, mock은 `data/mock/experiment-v1`에 저장했다. 서로 다른 스냅샷/질문/결과 파일을 사용하며 한 FAISS에 혼합하지 않는다. 운영의 초기 탐색용 빈 목록 스냅샷 `production-final`도 최종 평가 데이터와 구분한다.

### 2.1 사용 API 및 보존 필드

| API | 사용 내용 | 처리 |
|---|---|---|
| `GET /api/public/v1/organizations/search` | organizationId, name | 문자열 cursor 순회, 단체 ID 중복 제거 |
| `GET /api/public/v1/organizations/{organizationId}/items` | itemId, name, availableQuantity, totalQuantity, isActive, rentalDuration, description, guaranteedGoods | 정수 cursor 순회, 단체 ID 일치 검사 |
| `GET /api/public/v1/items/{itemId}` | itemUnits, borrowerRequirements, itemManagementType, level | 요청 경로의 itemId로 목록과 결합 |

Swagger 명세 자체는 검색 문서로 사용하지 않는다. 단체/물품 이름과 ID, 수량, 활성 여부, 기간 원값, 설명, 담보, 유닛 라벨/상태, 입력 요구 항목, 관리 유형/level, 출처 URL, 목록·상세 수집 시각을 문서화한다. 실제 대여자의 이름·학번·연락처 값은 조회하지 않는다. borrowerRequirements의 ‘학번’, ‘학과’는 입력 요구 항목의 라벨이다. 이미지 URL과 인증 헤더는 문서에 저장하지 않는다.

`manifest.json`에는 종류(real_api/mock), 키워드, 시작/종료 시각, 요청 수, 단체별 목록 완료 여부, 오류, 문서 메타데이터를 기록한다. 목록 실패/상세 실패/null을 ‘물품 없음’이나 ‘조건 없음’으로 치환하지 않는다. 정상 조회 후 빈 목록은 실패와 구분한다. 전체 수량과 대여 가능 수량의 차이를 모두 대여 중으로 해석하지 않는다.

### 2.2 MOCK의 구성과 사용 내역

| 단체 ID | 가상 단체 | 항목 수 | 검증 포인트 |
|---|---|---:|---|
| 101 | 가상누리대학교 컴퓨터공학과 | 6 | 거치대 대여 가능 4개, RX-7 담보/기간, 축구공 상태 |
| 102 | 가상누리대학교 총학생회 | 6 | 같은 이름 거치대는 2개, PB-20000 비활성 |
| 103 | 가상한빛대학교 사진동아리 | 6 | ‘야간 촬영 흔들림 방지’ 설명의 삼각대 의미 검색 |
| 104 | 가상한빛대학교 체육학과 | 6 | 우산(itemId 10406) 상세 조회 실패 |
| 105 | 가상누리대학교 수집실패동아리 | 확인 불가 | 목록 조회 실패; 수집 항목 0개는 실제 빈 재고가 아님 |

101–104의 물품은 거치대·축구공·RX-7 마이크·PB-20000 보조배터리·삼각대·우산이다. 기본 전체 수량은 6개이며 UNIT/NON_UNIT, 6개 상태 enum, 필수/선택 입력 항목을 포함한다. 물품 ID는 `단체 ID × 100 + 순번`이다. 모든 문서에 MOCK 표시를 넣고 출처는 `mock.retrivr.invalid`로 구별한다.

가상 클라이언트가 반환한 응답을 실제 `collect()`로 변환했다. 검색 두 페이지와 단체 목록 두 페이지, 키워드 간 중복 단체를 구성하여 실제 수집 처리도 거친다. manifest의 요청 수 37은 **가상 클라이언트 함수 호출 수**이며 외부 HTTP 요청은 0회다. HTTP 503 두 건은 상세/목록 실패를 재현하기 위해 의도적으로 발생시켰다.

### 2.3 운영 최종 수집 내역

| 단체 ID | 단체명 | 수집 물품 종수 | 목록 완료 |
|---|---|---:|---|
| 9 | 건국대학교 동아리연합회 | 0 | 완료 |
| 3 | 건국대학교 도서관자치위원회 | 4 | 완료 |
| 2 | 건국대학교 생명과학대학 학생회 시즌 | 7 | 완료 |
| 7 | 리트리버 | 0 | 완료 |

단체 3의 물품은 8핀 충전기·구형 노트북 충전기·C타입 충전기·우산, 단체 2의 물품은 담요·공학용 계산기·단우산·장우산·실험복·케이블·보조배터리다. 최종 스냅샷은 조회 17회(검색 2 + 목록 4 + 상세 11), 오류 0건이다. 사전 검색 2회와 초기 리트리버 스냅샷 2회를 포함한 운영 확인 전체 조회는 21회다. 세 종류의 public 조회 API에서 무인증 성공을 확인했다. 다른 API의 인증 여부까지 일반화하지 않는다.

이 규모는 키워드로 확보한 범위이며 운영 전체 데이터 규모가 아니다. 빈 목록 두 건 역시 해당 수집 시점의 API 결과다. 라벨에 ‘파손’이 있으나 status가 AVAILABLE인 유닛도 관찰되어, 표시명과 상태 코드의 불일치는 운영 데이터 품질 검토 대상으로 남긴다.

### 2.4 제출 자료와 재현 한계

`data/` 없이도 다음을 제출해 평가 근거를 확인할 수 있다.

- `src/`의 구현과 mock 생성기, `tests/`, `pyproject.toml`, `uv.lock`, `.env.example`.
- 이 문서, `results/report.md`, `results/evaluation.md`, `README.md`.
- `results/mock-questions.json`, `results/mock-review.json`: 고정 질문, 정답 근거, 검색 순서, 생성 답변, 판정, 프롬프트.
- `results/production-questions.json`, `results/production-review.json`: 운영 고정 질문과 최종 실행 근거.

실제 `.env`, 토큰, 가상환경, Git 관리 정보는 제출하지 않는다. `results/run-*.json`은 로컬 상세 기록이며 제출 필수 목록과 분리한다. 리뷰 JSON에는 원 데이터 전체 대신 평가에 필요한 질문/근거/답변을 포함하므로 데이터 폴더 미제출 조건에서도 결과를 읽을 수 있다.

mock 데이터 재생성은 네트워크 없이 가능하다. 기존 파일을 덮어쓰지 않도록 새 경로를 사용한다.

```bash
uv sync
uv run python src/create_mock_data.py --output data/mock/reproduced --cases results/reproduced-questions.json
uv run python src/capstone_compare.py --snapshot data/mock/reproduced --cases results/reproduced-questions.json --mode plan --generate
```

재생성은 업무 값과 질문을 재현하지만 수집 시각이 달라져 파일 내용/해시까지 같지는 않다. 새 스냅샷으로 Baseline부터 다시 실행해야 한다. 과거 운영 상태는 재조회로 정확히 복원할 수 없으며 당시 결과는 제출한 리뷰 기록을 기준으로 판단한다. 모델 응답도 반복 실행에서 달라질 수 있다.

## 3. 처리 구조

```text
API 응답 또는 MockClient
  → collect_api: 페이지네이션·중복 제거·상세 결합·오류 기록
  → 물품별 문서 + 단체 목록 + manifest
  → TextLoader → 본문 Splitter(900자 / overlap 150자)
  → 모든 청크에 식별·출처·시각 헤더 복원
  → text-embedding-3-small → FAISS similarity Top-3
  → 근거 제한 Prompt → gpt-4o-mini(temperature=0)
```

API 호출은 수집 단계에서만 수행한다. FAISS는 실행 중 메모리에서 구축하며 영속 인덱스 캐시는 아직 구현하지 않았다. 같은 compare 실행에서는 질문 임베딩을 두 검색 방식이 공유한다. 강의의 다른 실습 예제와 `rag_core.py`는 기존 구조를 유지한다.

## 4. 검색 개선과 생성 개선의 분리

Hybrid는 BM25와 벡터 후보를 각각 최대 `max(3×k, 10)`개 모은 뒤 RRF 상수 60으로 합쳐 Top-K를 반환한다. BM25 토큰은 영문/숫자/한글 단어와 한글 2-gram이다. 기존 rank-bm25 의존성을 사용하며 별도 형태소 분석기는 추가하지 않았다.

mock Baseline에서 다른 단체 동명 물품이 Top-3에 섞여 Hybrid를 비교했다. 다른 단체 청크는 줄었지만 정답 검색률과 주요 답변 정확도 향상은 없었다. 생성 단계의 기간 단위 추정 오류는 검색 문제와 별개여서 시스템 지시/사용자 자료 분리와 기간 규칙으로 대응했다.

후속 회귀인 ‘수집 실패→물품 없음’은 `collection_failure_answer()`가 처리한다. 질문에 해당 단체 전체 이름이 있고 수집 실패 목록 문서가 검색된 경우에만 출처/시각과 함께 확인 불가를 반환한다. 기본 Baseline Prompt에는 적용하지 않고 `refine_generation.py`의 개선 실행에 적용한다. 별칭·이름 일부만 질문하거나 실패 목록이 검색되지 않으면 이 보호가 보장되지 않는다.

## 5. 평가 설계

mock 고정 질문 10개는 생성기의 `cases()`로 작성하고, 운영 질문 10개는 실제 문서에서 prepare 후 실행 전에 검토·수정했다. 두 데이터셋의 수치는 합산하지 않는다. 질문 원문/정답 근거는 각각의 questions JSON에 있다.

Retrieval Hit는 Top-K 중 같은 청크에 정답 문서 ID와 근거 문자열이 존재하는지 판단한다. mock Q8–Q10, 운영 Q9–Q10처럼 답이 없는 질문은 분모에서 제외하고 Generation의 답변 제한을 확인한다. 복합 질문의 모든 조건 충족은 이 지표만으로 보장하지 않는다.

Generation은 주요 내용의 근거 일치, 질문 응답, 답변 제한을 검토한다. 생성 품질은 저장된 답변과 근거 문서를 대조한 모델 보조 판정이다. 독립적인 사람 검수나 별도 자동 채점 모델의 결과는 아니므로 참고 지표로 사용한다. 비교 모드는 데이터·메타데이터·질문 해시와 모델/Top-K/생성 여부 일치를 요구한다. 최종 mock 결과는 기존 v2 답변을 재사용하고 Q9만 코드로 교체했으며 모델 전체를 재실행한 결과가 아니다. 운영 개선은 동일 검색 근거에서 10개 답변을 새로 생성했다. 운영 Hit@3는 8/8, 답변 제한은 1/2에서 2/2로 바뀌었으나 출처·시각 표시는 10/10에서 9/10으로 감소했다.

## 6. 한계와 후속 작업

수집 범위/시점 제한, 목록·상세의 비동시성, 일부 검색 결과를 전체 목록으로 오인할 위험이 있다. 소규모 질문셋은 운영 품질을 일반화하기에 부족하다. 상세 근거를 사용하고도 목록 URL만 인용하는 답변이 있어 출처 연결도 개선해야 한다. 운영에선 별칭, 다중 단체 비교, 수량 변화, 오류/누락 시나리오를 늘리고 단체 메타데이터 필터·출처 검증·실패 상태의 구조화 처리를 검토한다. 실측 결과와 현재 미해결 문제는 evaluation.md를 따른다.


## 7. 실습 요구사항과 구현 위치

| 실습 요구사항 | 구현 및 확인 위치 |
|---|---|
| 문제 정의·대상 사용자·문서 범위 | 이 문서 1~2절 |
| 기본 RAG 파이프라인 | capstone_compare.py의 load_snapshot(), main(), answer_with_retriever() |
| 검색된 문서·출처 확인 | inspect(), evaluate()가 반환/저장하는 retrieved의 content와 metadata |
| 고정 질문 8~10개 | mock/운영 각각 10문항, evaluation.md에 질문 원문 수록 |
| Baseline 및 최소 한 가지 개선 | FAISS similarity와 Hybrid를 같은 Prompt로 비교 |
| 동일 데이터·질문으로 전후 비교 | fingerprint 및 config 일치 확인 |
| Retrieval/Generation 분리 평가 | hit 및 generation_review, evaluation.md의 분리된 지표 |
| 문서에 없는 질문 처리 | expected_keyword=null은 Hit Rate 분모에서 제외 |
| 실패 원인에 맞춘 생성 개선 | STRICT_PROMPT와 collection_failure_answer(), refine_generation.py 실행 |
| 결과·한계 기록 | evaluation.md의 mock/운영 비교와 미흡 사항 |

평가의 중심 파일은 capstone_compare.py, design.md, evaluation.md다. 실행하려면 수집/문서 저장을 담당하는 collect_api.py, mock 생성기, 질문 JSON 등 보조 파일도 필요하다. 세 파일이 평가 대상이라는 의미와 세 파일만으로 실행할 수 있다는 의미는 구별한다. 전체 코드는 기존 저장소 구조로 제출하고 data/는 제외할 수 있다.

검색 개선과 생성 개선의 실행 경로도 구별한다. `--mode compare`는 Baseline과 Hybrid에 같은 기본 Prompt를 사용한다. `refine_generation.py --baseline 결과파일 --output 새결과파일`은 저장된 검색 문맥에 개선 Prompt와 실패 처리를 적용한다. 따라서 Hybrid 검색 개선의 효과와 Prompt 변경의 효과를 한 수치로 합치지 않았다.
