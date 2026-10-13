# Moving from local retrieval to Amazon Bedrock Knowledge Bases

Local TF-IDF retrieval (default) is for learning. Real regulations need semantic search, so use a Knowledge Base.

1. `scripts/poc3_upload_corpus.sh` (creates the S3 bucket, uploads `regulations/` and `procedures/`).
2. Bedrock console > Knowledge Bases > Create with vector store.
   - Data source: the S3 bucket above.
   - Embeddings model: an Amazon Titan or Cohere embed model you have access to.
   - Vector store: choose the cheapest option offered in your account/region (quick-create may provision OpenSearch Serverless, which bills hourly even when idle; Amazon S3 Vectors may be available and cheaper). Check current pricing before creating.
   - Chunking: hierarchical or default is fine; keep each section heading with its text.
3. Click **Sync** after any document change.
4. `export KB_ID=<knowledge base id>` then `python poc3_compliance/agent.py` (no --mock).
5. Test retrieval alone in the console "Test knowledge base" panel first; if retrieval is bad, the agent will be bad.
6. **Delete the Knowledge Base and vector store when done** to stop charges.

Citations: `retriever.py` derives ids from the doc title and `## section` markers in each chunk. If your real documents are PDFs, adapt `BedrockKBRetriever.search` to use page numbers or metadata (and keep the rule that a citation must be a retrieved id).
