import asyncio
import ollama
from sqlalchemy import select

from app.db import async_session
from app.models.models import KBDoc

EMBED_MODEL = "nomic-embed-text"


def get_embedding(text: str) -> list[float]:
    response = ollama.embeddings(model=EMBED_MODEL, prompt=text)
    return response["embedding"]


async def main():
    async with async_session() as session:
        result = await session.execute(select(KBDoc))
        docs = result.scalars().all()

        for doc in docs:
            print(f"Embedding: {doc.title}")
            doc.embedding = get_embedding(doc.content)

        await session.commit()
        print(f"Done. Embedded {len(docs)} docs.")


if __name__ == "__main__":
    asyncio.run(main())