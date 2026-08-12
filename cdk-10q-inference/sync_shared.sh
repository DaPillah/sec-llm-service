#!/bin/bash
set -e
cp shared/sec_edgar.py lambda-10q-inference/sec_edgar.py
cp shared/extractor.py lambda-10q-inference/extractor.py
cp shared/exceptions.py lambda-10q-inference/exceptions.py
cp shared/pipeline.py lambda-10q-inference/pipeline.py
cp shared/sec_edgar.py lambda-rag/sec_edgar.py
cp shared/extractor.py lambda-rag/extractor.py
cp shared/exceptions.py lambda-rag/exceptions.py
cp shared/pipeline.py lambda-rag/pipeline.py
echo "Synced shared/ into lambda-10q-inference/ and lambda-rag/"
