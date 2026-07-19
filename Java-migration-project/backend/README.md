# Java Migration Assistant — Backend

AI-powered backend for analysing and migrating Java projects. Phase 1 covers file ingestion only.

## Requirements

- Python 3.12+

## Setup

```bash
cd backend

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux

# Install dependencies
pip install -r requirements.txt
```

## Run

```bash
uvicorn app.main:app --reload
```

Server starts at **http://localhost:8000**

## Endpoints

| Method | Path      | Description                        |
|--------|-----------|------------------------------------|
| GET    | /health   | Health check                       |
| POST   | /upload   | Upload a ZIP file for extraction   |

Interactive docs: http://localhost:8000/docs

## Upload Example

```bash
curl -X POST http://localhost:8000/upload \
  -F "file=@my-java-project.zip"
```

### Response

```json
{
  "message": "Upload successful",
  "extracted_folder": "C:\\Java-migration-project\\backend\\workspace\\a3f1c2...",
  "file_count": 42
}
```

## Project Structure

```
backend/
├── app/
│   ├── main.py            # FastAPI app, logging, lifespan
│   ├── config.py          # Centralised settings (pydantic-settings)
│   ├── routers/
│   │   └── upload.py      # POST /upload route
│   ├── services/
│   │   └── upload_service.py  # ZIP validation, save, extract
│   ├── models/
│   │   └── upload.py      # Pydantic response schema
│   └── utils/             # Shared helpers (future use)
├── uploads/               # Raw uploaded ZIPs (git-ignored)
├── workspace/             # Extracted project trees (git-ignored)
├── requirements.txt
├── .env
└── README.md
```

## Configuration

Override defaults via `.env` or environment variables:

| Variable             | Default | Description                  |
|----------------------|---------|------------------------------|
| DEBUG                | false   | Enable debug logging         |
| MAX_UPLOAD_SIZE_MB   | 100     | Max allowed upload size (MB) |
