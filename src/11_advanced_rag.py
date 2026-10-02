from dotenv import load_dotenv
from langchain_classic.retrievers.multi_query import MultiQueryRetriever
from langchain_openai import ChatOpenAI

from rag_core import build_retriever

load_dotenv()

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
)
retriever = build_retriever(
    file_path="data/sample.txt",
    k=3,
)


def rewrite_query(question: str) -> str:
    prompt = f"""
다음 사용자 질문의 의미를 바꾸지 말고,
문서 검색에 적합한 한 문장의 검색 질의로 다시 작성하세요.
불필요한 설명은 하지 말고 검색 질의만 출력하세요.

[사용자 질문]
{question}
"""
    return llm.invoke(prompt).content.strip()


def show_search(title: str, query: str):
    print(f"\n=== {title} ===")
    print("Query:", query)
    docs = retriever.invoke(query)
    for i, doc in enumerate(docs, start=1):
        print(f"{i}. {doc.page_content}")


question = "책 빌리면 며칠 안에 갖다 줘야 해?"
rewritten = rewrite_query(question)

print("=== Query Rewrite ===")
print("원래 질문:", question)
print("Rewrite:", rewritten)
show_search("원래 질문", question)
show_search("Rewrite 질문", rewritten)


def expand_query(question: str) -> str:
    prompt = f"""
다음 질문을 문서 검색에 사용할 것입니다.
질문의 의미를 유지하면서 관련 키워드와 유사 표현을 5개 정도 추가하여
한 줄의 검색 질의로 만들어 주세요.
설명은 하지 마세요.

[질문]
{question}
"""
    return llm.invoke(prompt).content.strip()


question = "노트북은 어디에서 사용할 수 있나요?"
expanded = expand_query(question)

print("\n=== Query Expansion ===")
print("원래 질문:", question)
print("Expansion:", expanded)
show_search("원래 질문", question)
show_search("Expansion 질문", expanded)


def decompose_query(question: str) -> list[str]:
    prompt = f"""
다음 복합 질문을 문서 검색에 적합한 독립적인 하위 질문으로 나누세요.
각 줄에 질문 하나만 출력하세요.
번호나 설명은 붙이지 마세요.

[복합 질문]
{question}
"""
    result = llm.invoke(prompt).content.strip()
    return [
        line.strip("- ").strip()
        for line in result.splitlines()
        if line.strip()
    ]


print("\n=== Query Decomposition ===")
complex_question = "평일 운영시간과 대출 가능 권수, 대출기간을 한 번에 알려 주세요."
sub_questions = decompose_query(complex_question)

all_docs = []
seen = set()
for q in sub_questions:
    print("-", q)
    docs = retriever.invoke(q)
    for doc in docs:
        if doc.page_content not in seen:
            seen.add(doc.page_content)
            all_docs.append(doc)

print("통합 검색 문서 수:", len(all_docs))


def route_query(question: str) -> str:
    prompt = f"""
다음 질문을 아래 셋 중 하나로 분류하세요.
REGULATION, PRODUCT, WEB
설명 없이 분류명만 출력하세요.

질문: {question}
"""
    return llm.invoke(prompt).content.strip().upper()


print("\n=== Query Routing ===")
print(route_query("최신 AI 규제 뉴스가 궁금합니다."))


def query_module(question: str) -> str:
    return rewrite_query(question)


def retrieval_basic(query: str):
    return retriever.invoke(query)


def post_retrieval_module(docs):
    return docs


def generation_module(question: str, docs) -> str:
    context = "\n\n".join(doc.page_content for doc in docs)
    prompt = f"""
제공된 문서만 근거로 질문에 답하세요.
문서에서 확인할 수 없는 내용은 추측하지 마세요.

[문서]
{context}

[질문]
{question}
"""
    return llm.invoke(prompt).content.strip()


def run_modular_rag(question: str, retrieval_module) -> dict:
    query = query_module(question)
    docs = retrieval_module(query)
    docs = post_retrieval_module(docs)
    answer = generation_module(question, docs)
    return {
        "question": question,
        "query": query,
        "docs": docs,
        "answer": answer,
    }


print("\n=== Modular RAG: basic ===")
basic_result = run_modular_rag(
    "책 빌리면 며칠 안에 돌려줘야 하나요?",
    retrieval_basic,
)
print("검색 Query:", basic_result["query"])
print("검색 문서 수:", len(basic_result["docs"]))
print("최종 답변:", basic_result["answer"])

multi_query_retriever = MultiQueryRetriever.from_llm(
    retriever=retriever,
    llm=llm,
    include_original=True,
)


def retrieval_multi(query: str):
    return multi_query_retriever.invoke(query)


print("\n=== Modular RAG: multi-query ===")
multi_result = run_modular_rag(
    "책 빌리면 언제까지 갖다 줘야 하나요?",
    retrieval_multi,
)
print("검색 Query:", multi_result["query"])
print("검색 문서 수:", len(multi_result["docs"]))
print("최종 답변:", multi_result["answer"])
