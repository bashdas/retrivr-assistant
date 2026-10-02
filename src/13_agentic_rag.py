from typing import TypedDict

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph

from rag_core import build_retriever, format_docs

load_dotenv()


class RAGState(TypedDict):
    original_question: str
    question: str
    context: str
    answer: str
    relevance: str
    retry_count: int


llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
)
retriever = build_retriever(
    file_path="data/sample.txt",
    k=3,
)


def retrieve(state: RAGState):
    docs = retriever.invoke(state["question"])
    context = format_docs(docs)

    print("\n[retrieve]")
    print("검색 질문:", state["question"])
    print(context)

    return {"context": context}


grade_prompt = ChatPromptTemplate.from_template("""
다음 질문에 답하는 데 아래 검색 문서가 충분히 관련 있는지 판단하세요.

GOOD: 질문에 답하는 데 필요한 핵심 정보가 문서에 있음
BAD: 질문과 무관하거나 핵심 정보가 부족함

GOOD 또는 BAD 중 하나만 출력하세요.

[질문]
{question}

[검색 문서]
{context}
""")


def grade(state: RAGState):
    messages = grade_prompt.invoke({
        "question": state["original_question"],
        "context": state["context"],
    })

    result = llm.invoke(messages).content.strip().upper()
    relevance = "good" if result.startswith("GOOD") else "bad"

    print("\n[grade]")
    print("평가:", relevance)

    return {"relevance": relevance}


rewrite_prompt = ChatPromptTemplate.from_template("""
다음 질문을 문서 검색에 더 적합한 표현으로 다시 작성하세요.
원래 의미는 유지하세요.
검색 질의 한 문장만 출력하세요.

[원래 질문]
{question}
""")


def rewrite(state: RAGState):
    messages = rewrite_prompt.invoke({
        "question": state["question"],
    })
    rewritten = llm.invoke(messages).content.strip()

    print("\n[rewrite]")
    print("이전 질문:", state["question"])
    print("새 질문:", rewritten)

    return {
        "question": rewritten,
        "retry_count": state["retry_count"] + 1,
    }


generate_prompt = ChatPromptTemplate.from_template("""
당신은 제공된 문서를 근거로 답하는 질문-답변 도우미입니다.

규칙:
1. 아래 문서에 있는 내용만 근거로 답하세요.
2. 문서에 없는 내용은 추측하지 마세요.
3. 간결하고 명확하게 답하세요.

[문서]
{context}

[사용자 원래 질문]
{question}

[답변]
""")


def generate(state: RAGState):
    messages = generate_prompt.invoke({
        "context": state["context"],
        "question": state["original_question"],
    })
    answer = llm.invoke(messages).content.strip()

    print("\n[generate]")
    print("답변:", answer)

    return {"answer": answer}


def fallback(state: RAGState):
    answer = (
        "현재 연결된 문서에서 질문에 답할 만한 "
        "충분한 근거를 찾지 못했습니다."
    )
    print("\n[fallback]")
    print(answer)
    return {"answer": answer}


def decide_after_grade(state: RAGState):
    if state["relevance"] == "good":
        return "generate"

    if state["retry_count"] >= 2:
        return "fallback"

    return "rewrite"


builder = StateGraph(RAGState)

builder.add_node("retrieve", retrieve)
builder.add_node("grade", grade)
builder.add_node("rewrite", rewrite)
builder.add_node("generate", generate)
builder.add_node("fallback", fallback)

builder.add_edge(START, "retrieve")
builder.add_edge("retrieve", "grade")

builder.add_conditional_edges(
    "grade",
    decide_after_grade,
    {
        "generate": "generate",
        "rewrite": "rewrite",
        "fallback": "fallback",
    },
)

builder.add_edge("rewrite", "retrieve")
builder.add_edge("generate", END)
builder.add_edge("fallback", END)

graph = builder.compile()

question = "책 빌리면 며칠 안에 돌려줘야 하나요?"

initial_state = {
    "original_question": question,
    "question": question,
    "context": "",
    "answer": "",
    "relevance": "",
    "retry_count": 0,
}

result = graph.invoke(initial_state)

print("\n============================")
print("[최종 결과]")
print("원래 질문:", result["original_question"])
print("마지막 검색 질문:", result["question"])
print("재검색 횟수:", result["retry_count"])
print("최종 답변:", result["answer"])

print("\n[실행 이벤트]")
for event in graph.stream(initial_state):
    print(event)
