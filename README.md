# Retrivr Assistant

사용자가 제공한 학교·학과·단체 키워드로 수집한 단체와 물품 정보를 안내하는 스냅샷 RAG입니다. 사용자 소속 조회 기능은 없으며 질문마다 API를 호출하지 않습니다.

## 데이터와 구조

실제 public API 응답 → 물품별 UTF-8 문서 → TextLoader → RecursiveCharacterTextSplitter → OpenAI Embedding → FAISS → Retriever → Prompt → LLM.

단체별 목록 문서도 함께 저장합니다. 각 청크에 단체명/ID, 물품명/ID, 출처, 수집 시각을 유지합니다. 이미지 URL은 검색에 필요하지 않고 서명 정보가 포함될 수 있어 저장하지 않습니다. 수집 키워드로 확보한 범위만 검색할 수 있습니다. 검색된 일부 문서는 전체 목록이 아니며 수량과 상태는 실시간 값이 아닙니다.

## 설치

Python 3.11과 uv를 사용합니다. 기존 pyproject.toml의 의존성을 그대로 사용하며 uv.lock으로 설치 버전을 고정했습니다.

```bash
uv sync
cp .env.example .env
```

`.env`에 `OPENAI_API_KEY`를 설정합니다. `RETRIVR_API_TOKEN`은 인증이 필요한 환경에서만 설정합니다. 키를 명령행 인자나 Git에 넣지 마세요. EC2 테스트 서버의 세 조회 API는 무인증 HTTP 200을 확인했습니다. 운영 서버의 같은 세 조회 API도 최종 검증에서 무인증 성공을 확인했습니다. 추적 기본값은 비활성입니다.

## 수집

아래 `학교명`을 실제 수집 키워드로 바꾸세요. 여러 키워드는 `--keyword`를 반복합니다.

```bash
uv run python src/collect_api.py --keyword '학교명' --keyword '단체명' --output data/snapshots/first --max-requests 100
```

새 디렉토리에만 저장하므로 이전 스냅샷이 섞이지 않습니다. 호출 수는 검색 페이지 수 + 단체별 물품 목록 페이지 수 + 중복 제거된 물품 수입니다. 기본 상한 100회, 요청당 시간 제한 20초이며 자동 재시도는 없습니다. 상한 초과·HTTP 오류·반복 커서는 누락으로 기록합니다. 일부 실패 시 종료 코드 2와 manifest.errors를 확인하세요. 실패를 빈 목록으로 해석하지 않습니다. 검색 실패와 단체별 목록 완료 여부는 manifest.json에서 확인합니다.

## 고정 질문과 호출 규모 확인

```bash
uv run python src/capstone_compare.py --snapshot data/snapshots/first --mode prepare
uv run python src/capstone_compare.py --snapshot data/snapshots/first --mode plan --generate
```

prepare는 실제 물품에서 10개 질문과 근거를 만들고 `results/questions.json`에 고정합니다. 질문 8개는 수량·조건·상태·표현 변경·복합 질문이며 2개는 사용자 소속과 미래 실시간 수량처럼 답할 수 없는 질문입니다. 생성된 질문/정답 근거를 검토한 뒤 같은 파일을 비교에 사용하세요. 상세가 누락된 질문은 Hit Rate에서 제외됩니다.

plan은 유료 호출 없이 청크 수, 문서 임베딩 토큰의 보수적 상한(UTF-8 바이트 수), 질문 임베딩 10회, Baseline 생성 10회 또는 비교 생성 20회의 규모를 보여줍니다. 토큰 상한은 실제 과금 토큰 수가 아닙니다. 실행마다 문서 임베딩을 다시 만들며 두 검색 방식은 같은 질문 벡터를 재사용합니다. 문서 임베딩 HTTP 호출 수는 SDK 배치 처리에 따라 달라집니다.

## Baseline 및 개선 비교

```bash
uv run python src/capstone_compare.py --snapshot data/snapshots/first --mode baseline --generate --output results/run-baseline.json
# Baseline의 검색 원문과 답변을 읽고 실패 원인을 기록한 후 실행
uv run python src/capstone_compare.py --snapshot data/snapshots/first --mode compare --generate --baseline results/run-baseline.json --reason '관찰한 실패 원인을 입력' --output results/run-compare.json
```

비교 후보는 BM25 + 벡터 검색의 RRF Hybrid입니다. 원 데이터·질문·모델·Top-K 설정이 Baseline과 다르면 비교를 거부합니다. 결과 JSON에는 검색된 전체 청크·출처·정답 포함 여부·최종 답변이 남습니다. Generation은 `generation_review`의 grounded/direct/abstains_if_unanswerable/notes를 사람이 검토하여 기록합니다. 자동 채점 결과처럼 해석하지 마세요. `--generate`를 생략하면 Retrieval만 평가합니다.

## 검증 및 현재 결과

```bash
uv run python -m unittest discover -s tests -v
```

테스트 데이터는 `fixture.invalid`를 사용하는 가상 데이터이며 서비스 성능 평가용이 아닙니다. mock 데이터로 Baseline·Hybrid·생성 개선 비교를 완료했습니다. 운영 키워드 범위에서 수집·검색·생성 최종 검증도 완료했으며 전체 운영 성능으로 일반화하지 않습니다. 상세 설계는 [results/design.md](results/design.md), 평가 상태는 [results/evaluation.md](results/evaluation.md)를 참고하세요.

전체 수량에서 대여 가능 수량을 뺀 값을 모두 대여 중으로 안내하지 않습니다. 일부 검색 문서만으로 전체 목록이나 이용 자격을 확정하지 않습니다. 후속 개선은 실제 Baseline 오류에 따라 결정합니다.

강의 스켈레톤 출처: https://github.com/comstudynews/rag-pipeline-lab2026 의 final_capstone/practice. 원본 강의 디렉토리는 수정하지 않았습니다.


## 권장 실험: mock 데이터

현재 주 실험은 `data/mock/experiment-v1`과 `results/mock-questions.json`입니다. 모든 단체/물품/출처는 가상입니다. 의도적으로 목록/상세 조회 오류를 각각 한 건 넣었습니다. 운영 서버 `https://www.retrivr.kr/`에서는 별도 스냅샷으로 최종 검증을 완료했습니다.

```bash
# 이미 제공된 v1은 그대로 사용. 새 데이터가 필요하면 새 경로로 생성
uv run python src/create_mock_data.py --output data/mock/experiment-v2 --cases results/mock-questions-v2.json
uv run python src/capstone_compare.py --snapshot data/mock/experiment-v1 --cases results/mock-questions.json --mode plan --generate
# 아래 실행은 유료 호출. 기존 결과를 덮어쓰지 않도록 새 output 경로 지정
uv run python src/capstone_compare.py --snapshot data/mock/experiment-v1 --cases results/mock-questions.json --mode baseline --generate --output results/run-mock-new-baseline.json
uv run python src/capstone_compare.py --snapshot data/mock/experiment-v1 --cases results/mock-questions.json --mode compare --generate --baseline results/run-mock-new-baseline.json --reason '관찰한 검색 문제' --output results/run-mock-new-compare.json
uv run python src/refine_generation.py --baseline results/run-mock-new-baseline.json --output results/run-mock-new-refined.json
```

refine_generation은 동일 검색 근거에 개선한 Prompt와 수집 실패 처리를 적용합니다. `--guard-only`는 저장된 답변에 실패 처리만 적용하여 유료 호출하지 않습니다. `.env`는 프로젝트 루트에서 읽고 기존 셸 환경변수보다 우선합니다.

실험 결과: Baseline/Hybrid Hit@3 모두 7/7, 다른 단체 청크 11/21 → 3/21. 주요 답변 근거 일치는 최종 처리 기준 9/10 → 10/10이며 Codex의 문서 대조 판정입니다. 작은 가상 데이터 결과이며 운영 품질 보장이 아닙니다. 중간 개선안의 회귀와 최종 답변 재사용 방식까지 [평가 기록](results/evaluation.md)에 공개했습니다.

운영 최종 검증 시 아래 형식으로 **대상 주소를 명시**하고 별도 스냅샷/질문 파일을 만듭니다. 아래는 새 스냅샷을 만드는 실행 형식입니다. 기존 검증 결과는 `results/production-review.json`에 있습니다.

```bash
uv run python src/collect_api.py --base-url https://www.retrivr.kr --keyword '실제 대상 키워드' --output data/snapshots/production-first --max-requests 20
```

운영에서 사용한 세 조회 API 경로와 무인증 접근은 확인했습니다. mock 데이터와 운영 데이터를 하나의 FAISS에 혼합하지 않습니다.


## 실습 보고서 및 제출

[종합실습 보고서](results/report.md)에 기획, 기술스택, 코드 구조, mock 개선 과정과 운영 최종 실행 결과를 정리했습니다. 운영은 단체 4곳·물품 11종, 문서 15개·청크 17개이며 정답 검색 8/8, 답 없는 질문 제한은 개선 전 1/2에서 개선 후 2/2였습니다. 개선 답변 1건의 출처·시각 누락도 기록했습니다.

안내된 평가 기준에 따라 **`data/`는 제출하지 않아도 됩니다.** [design.md](results/design.md)에 출처·범위·사용 필드·mock 생성 규칙·운영 사용 내역·재현 한계를 남겼습니다. 구현 코드, 설계/보고서/평가 문서, 질문·리뷰 JSON을 함께 제출하고 실제 `.env`와 토큰은 제외하세요. 로컬 데이터는 그대로 보존했습니다.
