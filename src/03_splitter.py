from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

loader = TextLoader("data/sample.txt", encoding="utf-8")
docs = loader.load()

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=120,
    chunk_overlap=20,
    add_start_index=True,
)

chunks = text_splitter.split_documents(docs)

print("원본 Document 수:", len(docs))
print("Chunk 수:", len(chunks))

for i, chunk in enumerate(chunks, start=1):
    print(f"\n--- Chunk {i} ---")
    print("metadata:", chunk.metadata)
    print(chunk.page_content)
