import os
import time
import logging

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_aws import BedrockEmbeddings, ChatBedrock
from langchain_community.vectorstores import FAISS
from pipeline import validate_request, retrieve_filing, extract_filing

from exceptions import ValidationError
from exceptions import TickerNotFoundError
from exceptions import FilingNotFoundError
from exceptions import InvokeError
from exceptions import LambdaContractError

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

EMBEDDING_MODEL_ID = os.environ["EMBEDDING_MODEL_ID"]
GENERATION_MODEL_ID = os.environ["MODEL_ID"]

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150  
TOP_K = 6
CHUNK_STRATEGY = "recursive_character"

'''
 Design notes (chunk_size=1000, overlap=150, k=6), based on manual testing
 against a real 10-Q (AAPL Q2 2026):
 - Single-fact lookups ("total net sales?") retrieve the correct table with
   ~1,700 input tokens, vs. ~21,500 for the full-document approach (Part 4).
 - Broad multi-topic questions within one domain (e.g. "risk factors AND
   legal proceedings") are both surfaced correctly within the top 6 chunks.
 - Questions combining two UNRELATED topics (e.g. a balance-sheet figure
   AND a narrative risk-factor topic) can crowd one topic out of the top-K,
   since a single combined query embedding is dominated by whichever topic
   matches more strongly. The prompt's "say so explicitly if not found"
   instruction correctly prevents hallucination in this case, but the
   answer is genuinely incomplete rather than wrong-but-confident.
'''

EXTRACTION_TOKEN_BUDGET = 1_000_000


def rag_answer(question, ticker, period, year, text):
    bedrock_client = boto3.client("bedrock-runtime", region_name="us-east-2")

    try:
        embeddings = BedrockEmbeddings(client=bedrock_client, model_id=EMBEDDING_MODEL_ID)

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
        )
        chunks = splitter.create_documents([text])

        vector_store = FAISS.from_documents(chunks, embeddings)

        retriever = vector_store.as_retriever(search_kwargs={"k": TOP_K})
        relevant_docs = retriever.invoke(question)

        context = "\n\n".join(doc.page_content for doc in relevant_docs)

        prompt = f"""Using only the SEC filing excerpts provided below, answer the following question. If the answer is not contained in the excerpts, say so explicitly.

Question: {question}

Filing excerpts ({ticker} {period} {year}):
{context}"""

        llm = ChatBedrock(
            client=bedrock_client,
            model_id=GENERATION_MODEL_ID,
            model_kwargs={"max_tokens": 1000},
        )

        start = time.perf_counter()
        response = llm.invoke(prompt)
        elapsed_ms = int((time.perf_counter() - start) * 1000)

    except Exception as e:
        raise InvokeError(f"RAG pipeline failed (embedding/retrieval/generation): {e}")

    return {
        "answer": response.content,
        "meta": {
            "model": GENERATION_MODEL_ID,
            "input_tokens": response.usage_metadata["input_tokens"],
            "output_tokens": response.usage_metadata["output_tokens"],
            "latency_ms": elapsed_ms,
            "chunks_retrieved": len(relevant_docs),
            "chunk_strategy": CHUNK_STRATEGY,
        },
    }


def process_request(payload):
    logger.info(f"Received payload: {payload}")

    validate_request(payload)
    logger.info("Validation passed")

    html = retrieve_filing(payload["ticker"], payload["year"], payload["period"])
    logger.info(f"Retrieved filing HTML, length={len(html)}")

    text = extract_filing(html, EXTRACTION_TOKEN_BUDGET)
    logger.info(f"Extracted text, length={len(text)}")

    result = rag_answer(payload["question"], payload["ticker"], payload["period"], payload["year"], text)
    logger.info(f"RAG pipeline complete, latency_ms={result['meta']['latency_ms']}")

    return result


def core_handler(event, context):
    try:
        result = process_request(event)
        logger.info("Request completed successfully")
        return {"ok": True, "data": result}
    except ValidationError as e:
        logger.warning(f"400 {e.__class__.__name__}: {e}")
        return {"ok": False, "error": e.__class__.__name__, "message": str(e), "status": 400}
    except (TickerNotFoundError, FilingNotFoundError) as e:
        logger.warning(f"404 {e.__class__.__name__}: {e}")
        return {"ok": False, "error": e.__class__.__name__, "message": str(e), "status": 404}
    except InvokeError as e:
        logger.error(f"502 {e.__class__.__name__}: {e}")
        return {"ok": False, "error": e.__class__.__name__, "message": str(e), "status": 502}
    except LambdaContractError as e:
        logger.error(f"500 {e.__class__.__name__}: {e}")
        return {"ok": False, "error": e.__class__.__name__, "message": str(e), "status": 500}