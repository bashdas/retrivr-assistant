from dotenv import load_dotenv
from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

# PREPROCESSING
# 1) 문서를 읽고 Chunk로 나눕니다.
loader = TextLoader("data/sample.txt", encoding="utf-8")
docs = loader.load()

splitter = RecursiveCharacterTextSplitter(
    chunk_size=120,
    chunk_overlap=20,
)
chunks = splitter.split_documents(docs)

# 2) Chunk를 Embedding하여 검색 가능한 Vector Store를 만듭니다.
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
vectorstore = FAISS.from_documents(chunks, embeddings)
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

# RUNTIME
# 3) 사용자 질문으로 관련 문서를 먼저 검색합니다.
question = "대출한 책을 연장할 수 있나요?"
retrieved_docs = retriever.invoke(question)

# 4) 검색된 Document를 Prompt에 넣을 하나의 Context 문자열로 합칩니다.
context = "\n\n".join(
    f"[문서 {i}]\n{doc.page_content}"
    for i, doc in enumerate(retrieved_docs, start=1)
)

prompt = ChatPromptTemplate.from_template("""
당신은 제공된 문서를 근거로 답하는 질문-답변 도우미입니다.
다음 규칙을 지키세요.
1. 제공된 문서에 있는 정보만 사용하세요.
2. 문서에서 확인할 수 없는 내용은 추측하지 마세요.
3. 답변은 한국어로 간결하게 작성하세요.

[문서]
{context}

[질문]
{question}

[답변]
""")

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
)

# 5) Prompt에 검색 Context와 질문을 채웁니다.
messages = prompt.invoke({
    "context": context,
    "question": question,
})

# 6) LLM이 검색된 근거를 사용해 최종 답변을 생성합니다.
response = llm.invoke(messages)

print("[검색 문서]")
print(context)
print("\n[최종 답변]")
print(response.content)
