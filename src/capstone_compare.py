from dotenv import load_dotenv
from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

# TODO 1 (14.3): 해결할 문제와 사용할 문서 범위를 먼저 정의하세요.
# 아래 샘플 문서를 그대로 사용해 흐름을 확인한 뒤 자신의 문서로 바꿔도 됩니다.

# TODO 2 (14.4): Baseline RAG를 완성하세요.
# 교재의 순서: Loader → Splitter → Embedding → Vector Store → Retriever
docs = None
chunks = None
embeddings = None
vectorstore = None
baseline = None

# TODO 3 (14.5): 8~10개의 고정 질문셋을 만드세요.
# 답이 문서에 없는 질문은 expected_keyword에 None을 사용합니다.
test_cases = []

# TODO 4 (14.6, 14.8): Baseline Retrieval 결과를 측정하세요.
def inspect(retriever, question: str):
    # Retriever로 관련 문서를 검색해 반환하세요.
    raise NotImplementedError


def hit(retrieved, expected_keyword: str) -> int:
    # 검색 결과 안에 expected_keyword가 있으면 1, 없으면 0을 반환하세요.
    raise NotImplementedError


def evaluate(name: str, retriever) -> float:
    # 문서에 답이 있는 질문만 Hit Rate에 포함하고 검색 결과도 함께 출력하세요.
    raise NotImplementedError


# TODO 5 (14.7): 현재 실패 원인에 맞는 개선 전략 하나를 적용하세요.
# 예: MMR / Hybrid / Reranker / Query Rewrite / Agentic RAG
improved = None

# TODO 6 (14.8): 동일한 질문셋으로 Baseline과 개선 Pipeline을 비교하세요.
# baseline_score = evaluate("Baseline", baseline)
# improved_score = evaluate("Improved", improved)

# Generation 평가에 사용할 Prompt와 Chat Model도 구성하세요.
prompt = None
llm = None


def answer_with_retriever(question: str) -> str:
    # 검색된 Document를 Context로 구성하고 Prompt → Chat Model로 답변을 생성하세요.
    raise NotImplementedError


# TODO 7 (14.9~14.10):
# results/design.md, results/evaluation.md에
# 문제 정의, 선택 이유, 평가 결과, 한계 등을 정리하고 제출 전 점검을 완료하세요.

if any(value is None for value in [docs, chunks, embeddings, vectorstore, baseline, improved, prompt, llm]):
    raise SystemExit("TODO 1~7을 교재 순서에 따라 완성한 뒤 실행하세요.")

print("종합실습 코드를 완성했습니다. 이제 동일 질문셋으로 개선 전·후를 비교하세요.")
