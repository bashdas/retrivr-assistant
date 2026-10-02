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

`.env`에 `OPENAI_API_KEY`를 설정합니다. `RETRIVR_API_TOKEN`은 인증이 필요한 환경에서만 설정합니다. 키를 명령행 인자나 Git에 넣지 마세요. 현재 확인한 세 조회 API는 무인증으로 HTTP 200을 반환했습니다. 추적 기본값은 비활성입니다.

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

테스트 데이터는 `fixture.invalid`를 사용하는 가상 데이터이며 서비스 성능 평가용이 아닙니다. 실제 키워드와 OpenAI 키가 아직 없어 Baseline·Generation·Hybrid 성능 수치는 미측정입니다. 상세 설계는 [results/design.md](results/design.md), 평가 상태는 [results/evaluation.md](results/evaluation.md)를 참고하세요.

전체 수량에서 대여 가능 수량을 뺀 값을 모두 대여 중으로 안내하지 않습니다. 일부 검색 문서만으로 전체 목록이나 이용 자격을 확정하지 않습니다. 후속 개선은 실제 Baseline 오류에 따라 결정합니다.

강의 스켈레톤 출처: https://github.com/comstudynews/rag-pipeline-lab2026 의 final_capstone/practice. 원본 강의 디렉토리는 수정하지 않았습니다.
