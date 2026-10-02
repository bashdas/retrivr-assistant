from dotenv import load_dotenv
from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

# 1) 원본 문서를 읽습니다.
loader = TextLoader("data/sample.txt", encoding="utf-8")
docs = loader.load()

# 2) 검색하기 좋은 크기의 Chunk로 나눕니다.
splitter = RecursiveCharacterTextSplitter(
    chunk_size=120,
    chunk_overlap=20,
)
chunks = splitter.split_documents(docs)

# 3) Chunk를 벡터로 변환해 FAISS에 저장합니다.
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
vectorstore = FAISS.from_documents(chunks, embeddings)

# 4) Vector Store를 Retriever 인터페이스로 감쌉니다.
# k=3은 관련 문서 3개를 반환하라는 뜻입니다.
retriever = vectorstore.as_retriever(
    search_kwargs={"k": 3}
)

# 5) 질문을 넣고 실제 검색 결과를 확인합니다.
question = "토요일에는 몇 시까지 운영하나요?"
results = retriever.invoke(question)

for i, doc in enumerate(results, start=1):
    print(f"\n[{i}] {doc.page_content}")
