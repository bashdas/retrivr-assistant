from langchain_community.document_loaders import TextLoader

loader = TextLoader(
    "data/sample.txt",
    encoding="utf-8",
)

docs = loader.load()

print("문서 개수:", len(docs))
print("\n[page_content]")
print(docs[0].page_content)
print("\n[metadata]")
print(docs[0].metadata)
