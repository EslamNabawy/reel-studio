# AI Toolbox

Collection of standalone Python AI utilities. Each subfolder is independent — install its own `requirements.txt` and run it directly. No shared package, no framework.

## Projects

| Folder | What it does | Entry point | Deps |
| --- | --- | --- | --- |
| `rag.py` | RAG search over a folder of PDFs. Chunks, embeds with `paraphrase-multilingual-MiniLM-L12-v2`, stores in ChromaDB, answers with Gemini. | `rag.py` | `requirements.txt` |
| `image_to_text/` | Image captioning / VQA with BLIP. Writes results to CSV. | `image_to_text/caption.py` | `image_to_text/requirements.txt` |
| `video_voiceover/` | Desktop app: add Arabic or English voice-over + burned subtitles to videos or images. GUI + CLI, packaged with PyInstaller. | `video_voiceover/app.py` | `video_voiceover/requirements.txt` |

## Setup

```bash
# global
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# per project
pip install -r image_to_text\requirements.txt
pip install -r video_voiceover\requirements.txt
```

## API keys

Put keys in `.env` at repo root (git-ignored):

```
GEMINI_API_KEY=your-key
```

`.env` is never committed. Keep `.env.example` keys documented instead.

## Layout

```
.env                  # secrets, ignored
.gitignore
requirements.txt      # root-level deps (rag.py)
rag.py
data/                 # PDFs loaded by rag.py (*.pdf ignored)
chroma_db/            # ChromaDB persistence (ignored, rebuildable)
image_to_text/
video_voiceover/
cvs merg/             # personal CVs, ignored
```

## Notes

- `chroma_db/`, `hf_models/`, `build/`, `dist/`, `output/`, `*.pdf` are git-ignored — regenerate or keep local.
- First run of BLIP / Whisper / sentence-transformers downloads models to `hf_models/` or the HF cache.
- Build the desktop exe with `video_voiceover\build.ps1`.
