from pathlib import Path

from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter


def load_and_split(file_path: str):
    """텍스트 파일을 읽고 검색용 Chunk로 나눕니다."""

    # 경로 오타를 초기에 잡기 위해 파일 존재 여부를 먼저 확인합니다.
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")

    # UTF-8 텍스트 파일을 LangChain Document로 읽습니다.
    loader = TextLoader(str(path), encoding="utf-8")
    docs = loader.load()

    # 03장과 동일한 크기를 사용해 앞뒤 실습 결과가 이어지게 합니다.
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=120,
        chunk_overlap=20,
    )
    return splitter.split_documents(docs)


def build_vectorstore(file_path: str = "data/sample.txt"):
    """Chunk를 Embedding하여 FAISS Vector Store를 만듭니다."""

    chunks = load_and_split(file_path)

    # 문서와 질문을 같은 Embedding 공간에서 비교하기 위한 모델입니다.
    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small"
    )

    # Chunk와 벡터를 FAISS에 저장합니다.
    return FAISS.from_documents(
        documents=chunks,
        embedding=embeddings,
    )


def build_retriever(file_path: str = "data/sample.txt", k: int = 3):
    """질문과 관련된 상위 k개 Document를 반환하는 Retriever를 만듭니다."""

    vectorstore = build_vectorstore(file_path)

    # similarity 검색 결과 중 상위 k개만 반환합니다.
    return vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": k},
    )


def format_docs(docs):
    """검색된 Document 목록을 LLM Prompt에 넣을 문자열로 합칩니다."""

    return "\n\n".join(
        f"[문서 {i}]\n{doc.page_content}"
        for i, doc in enumerate(docs, start=1)
    )
