# Docx-Consulting-AI-Agent

AI-powered document review agent for consulting deliverables. Works both as an **MCP server for ChatGPT** and as a **standalone REST API** for testing.

---

## Features

- 📄 Upload and analyze Word documents (.docx)
- ✏️ Get AI-powered editing suggestions
- ✅ Select and apply changes
- ⬇️ Download modified documents
- 🔄 Dual mode: ChatGPT integration + Standalone testing

---

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js & pnpm
- `uv` (recommended) or `pip`

### Installation

**Backend:**
```bash
cd backend
uv pip install -r requirements.txt
```

**Frontend:**
```bash
cd frontend
pnpm install
pnpm build
```

### Running the Server

```bash
cd backend
source .venv/bin/activate && python server.py
```

Server starts at: `http://localhost:8787`

---

## Usage

### Option 1: ChatGPT Integration (MCP Mode)

Connect ChatGPT to your MCP server:

1. **Expose server publicly** (for local development):
   ```bash
   ngrok http 8787
   ```

2. **Configure ChatGPT**:
   - Add MCP server in ChatGPT settings
   - SSE URL: `https://your-ngrok-url.ngrok-free.app/sse`

3. **Use in ChatGPT**:
   - Upload a .docx file to ChatGPT
   - Ask: "Make this document more formal"
   - Review suggestions in the widget
   - Select and apply changes

#### MCP Endpoints

- `GET /sse` - Server-Sent Events endpoint
- `POST /sse/messages` - MCP message handling

#### MCP Tools

- `upload_document` - Upload Word document (supports URL or base64)
- `analyze_document` - Analyze and get suggestions
- `apply_changes` - Apply selected changes

#### File Upload Troubleshooting

**Issue**: ChatGPT may truncate large files when using base64 encoding.

**Solution**: Use the `file_url` parameter instead:

1. **Upload your file to temporary hosting**:
   - [file.io](https://file.io) - Simple, temporary file hosting
   - [tmpfiles.org](https://tmpfiles.org) - Temporary file storage
   - Or any publicly accessible URL

2. **Get the download URL** from the hosting service

3. **In ChatGPT**, explicitly instruct it to use the URL:
   ```
   "Please upload this document using the file_url parameter with this URL: 
   https://file.io/your-file-url"
   ```

**Why this happens**: ChatGPT's MCP implementation has size limitations when sending base64-encoded content in tool arguments. Files larger than ~50KB may be truncated.

---

### Option 2: Standalone Testing (REST API Mode)

**Start Frontend:**
```bash
cd frontend
pnpm dev
```

**Open Browser:**
```
http://localhost:5173
```

Upload a document, enter a query, and test the full workflow!

#### REST API Endpoints

**Base URL:** `http://localhost:8787`

##### 1. Health Check
```bash
GET /
```
Response:
```json
{"status": "healthy", "message": "MCP Server is running"}
```

##### 2. Upload Document
```bash
POST /api/upload
Content-Type: multipart/form-data

file: <.docx file>
```
Response:
```json
{
  "doc_id": "uuid",
  "filename": "document.docx",
  "metadata": {
    "word_count": 664,
    "paragraph_count": 187
  }
}
```

##### 3. Analyze Document
```bash
POST /api/analyze
Content-Type: application/json

{
  "doc_id": "uuid",
  "request": "Make it more formal."
}
```
Response:
```json
{
  "doc_id": "uuid",
  "suggestions": [
    {
      "id": "suggestion-uuid",
      "paragraph_index": 0,
      "original": "don't",
      "suggested": "do not",
      "reason": "Replace contractions..."
    }
  ],
  "count": 1
}
```

##### 4. Apply Changes
```bash
POST /api/apply
Content-Type: application/json

{
  "doc_id": "uuid",
  "suggestion_ids": ["suggestion-uuid"]
}
```
Response:
```json
{
  "success": true,
  "applied_count": 1,
  "download_url": "/api/download/filename_modified.docx"
}
```

##### 5. Download Modified Document
```bash
GET /api/download/{filename}
```
Returns: Binary .docx file

---

## Testing with curl

### Complete Workflow Example

```bash
# 1. Upload
curl -X POST http://localhost:8787/api/upload \
  -F "file=@tests/1/Azure.docx"

# 2. Analyze (use doc_id from step 1)
curl -X POST http://localhost:8787/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"doc_id": "your-doc-id", "request": "Make it more formal."}'

# 3. Apply (use suggestion IDs from step 2)
curl -X POST http://localhost:8787/api/apply \
  -H "Content-Type: application/json" \
  -d '{"doc_id": "your-doc-id", "suggestion_ids": ["suggestion-id"]}'

# 4. Download
curl -o output.docx http://localhost:8787/api/download/filename_modified.docx
```

### Automated Testing

```bash
# Run automated test script
cd backend
uv run ../test_app.py
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   ChatGPT Desktop App                   │
│                                                         │
│  ┌───────────────────────────────────────────────────┐ │
│  │         Document Editor Widget (React)            │ │
│  └───────────────────────────────────────────────────┘ │
└──────────────────────┬──────────────────────────────────┘
                       │ MCP Protocol (SSE)
                       ↓
┌─────────────────────────────────────────────────────────┐
│              Backend Server (Python/Starlette)          │
│                                                         │
│  ┌──────────────┐              ┌──────────────────┐    │
│  │  MCP Server  │              │   REST API       │    │
│  │  /sse        │              │   /api/*         │    │
│  └──────────────┘              └──────────────────┘    │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │     Document Processing (python-docx)            │  │
│  │     - Extract text                               │  │
│  │     - Generate suggestions                       │  │
│  │     - Apply changes                              │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## Current Limitations

⚠️ **Suggestion Engine**: Currently uses basic rule-based logic:
- Detects contractions ("don't" → "do not")
- Shortens long paragraphs (>30 words)

**Recommendation**: Integrate an LLM (OpenAI API) for sophisticated document analysis.

---

## Project Structure

```
.
├── backend/
│   ├── server.py           # Main server (MCP + REST API)
│   ├── requirements.txt    # Python dependencies
│   └── uploads/            # Uploaded documents
├── frontend/
│   ├── src/
│   │   ├── App.jsx        # React widget
│   │   └── App.css        # Styles
│   └── package.json       # Node dependencies
├── tests/
│   └── 1/
│       ├── Azure.docx     # Test document
│       └── query.txt      # Test query
├── test_app.py            # Automated test script
└── README.md
```

---

## License

MIT
