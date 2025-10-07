from langchain_perplexity import ChatPerplexity
from langchain.chains import RetrievalQA
from .vectorstore import get_retriever
from .config import PPLX_API_KEY, LLM_MODEL

def answer_question(question, k=5, temperature=0.0, collection_name=None):
    retriever = get_retriever(k=k, collection_name=collection_name)
    llm = ChatPerplexity(
        model=LLM_MODEL,
        temperature=temperature,
        pplx_api_key=PPLX_API_KEY
    )
    qa = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=True
    )
    result = qa({"query": question})
    return result

