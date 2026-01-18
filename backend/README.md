# ChatGPT Word Document Editor App

A ChatGPT app that allows users to upload Word documents, request edits through natural language, and receive AI-powered suggestions that can be applied directly to the document.

## Features

- 📤 Upload Word (.docx) documents through ChatGPT
- 💬 Request edits using natural language (e.g., "make it more formal", "fix grammar")
- 🎯 View suggested edits in an interactive widget
- ✅ Select which suggestions to apply
- 📥 Download modified documents with changes applied

## Project Structure

```
├── backend/          # Python MCP server
│   ├── server.py     # Main MCP server with tools
│   ├── uploads/      # Temporary document storage
│   └── requirements.txt
├── frontend/         # React widget
│   ├── src/
│   │   ├── App.jsx   # Main component
│   │   └── ...
│   └── package.json
└── knowledge/        # Documentation
```

## Setup

### Backend (Python MCP Server)

1. Install Python dependencies:
```bash
cd backend
pip install -r requirements.txt
```

2. Run the MCP server:
```bash
python server.py
```

### Frontend (React Widget)

1. Install Node dependencies:
```bash
cd frontend
npm install
```

2. Build the widget:
```bash
npm run build
```

The built widget will be in `frontend/dist/index.html` and will be served by the MCP server.

## How It Works

### Architecture

1. **Python MCP Server**: Exposes three tools to ChatGPT:
   - `upload_document`: Accepts base64-encoded Word files
   - `analyze_and_suggest`: Generates edit suggestions based on user requests
   - `apply_changes`: Applies selected suggestions to the document

2. **React Widget**: Interactive UI that:
   - Displays suggestions from the MCP server
   - Allows users to select which changes to apply
   - Calls MCP tools via `window.openai.callTool()`

3. **ChatGPT**: Orchestrates the workflow:
   - Interprets user requests
   - Calls appropriate MCP tools
   - Narrates the process to the user

### Workflow

```
User uploads .docx → ChatGPT calls upload_document
                  ↓
User: "Make it more formal"
                  ↓
ChatGPT calls analyze_and_suggest
                  ↓
Widget displays suggestions
                  ↓
User selects suggestions → Widget calls apply_changes
                  ↓
ChatGPT asks for confirmation
                  ↓
User confirms → Document modified
                  ↓
Widget shows download link
```

## Testing Locally

### With MCP Inspector

```bash
npx @modelcontextprotocol/inspector@latest \
  --server-url http://localhost:8787/mcp \
  --transport http
```

### With ChatGPT

1. Expose your local server with ngrok:
```bash
ngrok http 8787
```

2. In ChatGPT:
   - Enable developer mode (Settings → Apps & Connectors → Advanced)
   - Add connector with your ngrok URL + `/mcp`
   - Start a new chat and add your connector

3. Test the workflow:
   - Upload a Word document
   - Ask ChatGPT to suggest edits
   - Review suggestions in the widget
   - Apply changes and download

## Technologies

- **Backend**: Python, MCP SDK, python-docx
- **Frontend**: React, Vite
- **Integration**: ChatGPT Apps SDK

## Current Limitations

- Track Changes are simulated (python-docx has limited Track Changes support)
- Suggestions are rule-based (can be enhanced with OpenAI API)
- Files stored temporarily on local filesystem
- Simple edit detection logic

## Future Enhancements

- [ ] Integrate OpenAI API for intelligent suggestions
- [ ] Add true Track Changes support
- [ ] Implement cloud storage (S3, Azure Blob)
- [ ] Add more sophisticated edit detection
- [ ] Support for more document formats
- [ ] User authentication and document management
