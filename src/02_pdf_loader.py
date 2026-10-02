from langchain_community.document_loaders import PyPDFLoader

# data 폴더의 텍스트 기반 PDF를 페이지 단위로 읽습니다.
loader = PyPDFLoader("data/sample.pdf")
docs = loader.load()

# Loader가 몇 개의 페이지 Document를 만들었는지 확인합니다.
print("페이지 단위 Document 개수:", len(docs))

# 처음 3개 페이지의 metadata와 일부 내용을 확인합니다.
for i, doc in enumerate(docs[:3], start=1):
    print(f"\n--- Document {i} ---")
    print("metadata:", doc.metadata)
    print(doc.page_content[:500])
