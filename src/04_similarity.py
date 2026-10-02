import math
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings

load_dotenv()
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")


def cosine_similarity(a, b):
    # 두 벡터가 같은 방향을 향하는 정도를 계산합니다.
    dot = sum(x * y for x, y in zip(a, b))

    # 각 벡터의 길이를 계산합니다.
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))

    # 내적을 두 벡터 길이의 곱으로 나누면 Cosine Similarity가 됩니다.
    return dot / (norm_a * norm_b)

sentences = [
    "도서는 최대 5권까지 대출할 수 있다.",
    "한 사람이 빌릴 수 있는 책은 최대 다섯 권이다.",
    "토요일 운영시간은 오전 10시부터 오후 5시까지이다.",
]

vectors = embeddings.embed_documents(sentences)

print("문장 1 vs 문장 2:", cosine_similarity(vectors[0], vectors[1]))
print("문장 1 vs 문장 3:", cosine_similarity(vectors[0], vectors[2]))
