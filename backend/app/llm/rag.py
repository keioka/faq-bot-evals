"""Simple RAG over the knowledge base with LlamaIndex: chunk by Markdown heading, embed, retrieve top-k.

The index lives in memory and is built once per process (about 20 chunks, one embedding call).
"""

from functools import cache

from llama_index.core import Document, VectorStoreIndex
from llama_index.core.node_parser import MarkdownNodeParser, SentenceSplitter
from llama_index.embeddings.openai import OpenAIEmbedding


@cache
def _retriever(kb: str, k: int, embed_model: str, chunk_size: int | None):
    """Split the knowledge base into one node per Markdown section and build an in-memory vector index.

    With chunk_size, each section is split again into chunks of about chunk_size tokens, so a broad
    section (e.g. "About Global-e") becomes several focused chunks.
    """
    nodes = MarkdownNodeParser().get_nodes_from_documents([Document(text=kb)])
    if chunk_size:
        nodes = SentenceSplitter(chunk_size=chunk_size, chunk_overlap=0)(nodes)
    index = VectorStoreIndex(nodes, embed_model=OpenAIEmbedding(model=embed_model))
    return index.as_retriever(similarity_top_k=k)


def retrieve(question: str, kb: str, k: int, embed_model: str, chunk_size: int | None = None) -> list[str]:
    """Return the text of the k chunks most similar to the question (whole sections when chunk_size is None)."""
    return [node.get_content() for node in _retriever(kb, k, embed_model, chunk_size).retrieve(question)]
