# PDF RAG (`rag.py`)

Semantic search + Gemini answers over a folder of PDFs.

## How it works

1. Reads every PDF in `data/`
2. Splits text into 1000-char chunks with 200-char overlap
3. Embeds with `paraphrase-multilingual-MiniLM-L12-v2`
4. Stores vectors in `chroma_db/` (collection `pdf_rag`)
5. On query: top-12 chunks go to Gemini as context

## Usage

```bash
python rag.py            # interactive prompt
python rag.py "question"  # one-shot
```

Drop PDFs into `data/`. ChromaDB is git-ignored and rebuilt on first run.

## Requires

`.env` with `GEMINI_API_KEY=...` at repo root.
