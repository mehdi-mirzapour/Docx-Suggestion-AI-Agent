# 📝 Docs Suggester AI (DocxAI)

> **Now with Native ChatGPT Panel Support! 🚀**

AI-powered document review agent for consulting deliverables. Works seamlessly inside **ChatGPT** via a custom interactive panel, or as a standalone REST API.

![Demo UI](demo_ui.png)

---

## ✨ Features

- **🎨 Interactive Widget**: Upload and edit documents directly inside ChatGPT (no external file hosts needed).
- **🧠 GPT-4o Integration**: Uses the latest AI models for high-quality consulting feedback.
- **🔒 Secure Connectivity**: Dynamically injects secure Ngrok tunnels for safe API communication.
- **⚡️ Smart Editing**: 
  - Detects tone issues (e.g., "don't" → "do not")
  - Flag long, complex paragraphs
  - Rewrite text for clarity and impact
- **⬇️ Direct Download**: Get your modified `.docx` file instantly from the panel.

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Node.js & npm
- `uv` (recommended) or `pip`

### 1. Installation

**Backend setup:**
```bash
cd backend
uv pip install -r requirements.txt
```

**Frontend setup:**
```bash
cd frontend
npm install
npm run build
```

**Widget Compilation:**
This connects the frontend to the backend logic.
```bash
# From project root
python3 inline_assets.py
```

### 2. Running the Server

You need two things running: the **backend server** and **ngrok** tunnel.

**Start the Backend:**
```bash
cd backend
python server.py
# Runs on http://localhost:8787
```

**Start Ngrok:**
```bash
ngrok http 8787
```
*Note the HTTPS URL provided by ngrok (e.g., `https://xxxx.ngrok-free.app`).*

---

## 🤖 Usage: ChatGPT Integration

This is the primary way to use the agent.

1.  **Configure ChatGPT**:
    -   Go to **GPT Builder** (`@Docs Suggester AI`).
    -   Add Action -> Import from URL: `https://your-ngrok-url.ngrok-free.app/sse`
    
2.  **Start Editing**:
    -   Just type: **"Open DocxAI Panel"**
    -   The interactive widget will appear above the chat.
    
3.  **Workflow**:
    -   **Upload**: Click the file input in the panel.
    -   **Analyze**: Type "Make this more professional" and click **Upload & Analyze**.
    -   **Review**: Select the suggestions you like.
    -   **Apply**: Click **Apply Changes**.
    -   **Download**: Click the download button to get your new file.

---

## 🛠️ Architecture: The "Proper" Solution

We implemented a robust **Dynamic Host Injection** architecture to solve the "localhost in cloud" problem.



1.  **Self-Contained Frontend**: The React widget is built into a single `index.html` file using `inline_assets.py`.
2.  **Runtime Injection**: When you request the panel, the backend updates the widget code on-the-fly with the current secure Ngrok URL.
3.  **Direct Communication**: The widget talks directly to your backend, bypassing ChatGPT's restrictive file handling limits.

---

## 🔌 API Reference (Standalone Mode)

You can also use the backend as a standard REST API.

**Base URL:** `http://localhost:8787`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/upload` | Upload `.docx` file |
| `POST` | `/api/analyze` | Get AI suggestions |
| `POST` | `/api/apply` | Apply selected edits |
| `GET` | `/api/download/{file}` | Download result |

---

## 📂 Project Structure

```
.
├── backend/
│   ├── server.py           # MCP Server + Injection Logic
│   └── requirements.txt    # Python dependencies
├── frontend/
│   ├── src/App.jsx         # React Widget Logic
│   └── dist/index.html     # Compiled Widget
├── inline_assets.py        # Build script for widget
└── README.md
```

## License

MIT
