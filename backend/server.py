import asyncio
import base64
import os
import uuid
from pathlib import Path
from typing import Any

from docx import Document
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Resource, Tool, TextContent
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize MCP server
app = Server("docx-editor-server")

# Storage for uploaded documents
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# In-memory storage for document metadata and suggestions
documents = {}
suggestions_store = {}


def extract_document_metadata(doc_path: str) -> dict:
    """Extract metadata from a Word document."""
    doc = Document(doc_path)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    
    return {
        "word_count": sum(len(p.split()) for p in paragraphs),
        "paragraph_count": len(paragraphs),
        "preview": paragraphs[0][:200] if paragraphs else "",
    }




def generate_suggestions(doc_path: str, request: str) -> list[dict]:
    """Generate AI-powered suggestions using GPT-4o-mini with batched processing."""
    doc = Document(doc_path)
    suggestions = []
    
    # Initialize OpenAI client
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key == "your_openai_api_key_here":
        # Fallback to rule-based if no API key
        return generate_suggestions_fallback(doc_path, request)
    
    client = OpenAI(api_key=api_key)
    
    # Collect non-empty paragraphs with their indices
    paragraphs_to_process = []
    for idx, paragraph in enumerate(doc.paragraphs):
        if not paragraph.text.strip():
            continue
        
        text = paragraph.text
        
        # Skip very short paragraphs (less than 10 words)
        if len(text.split()) < 10:
            continue
        
        paragraphs_to_process.append((idx, text))
    
    # Batch paragraphs to reduce API calls (process 5 paragraphs at a time)
    BATCH_SIZE = 5
    
    for batch_start in range(0, len(paragraphs_to_process), BATCH_SIZE):
        batch = paragraphs_to_process[batch_start:batch_start + BATCH_SIZE]
        
        # Create a combined prompt with all paragraphs in the batch
        batch_text = "\n\n---PARAGRAPH SEPARATOR---\n\n".join(
            f"[PARAGRAPH {i}]\n{text}" 
            for i, (idx, text) in enumerate(batch)
        )
        
        try:
            # Call GPT-4o-mini for batch suggestions
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": f"""You are a professional document editor. Analyze the given paragraphs and suggest improvements based on this request: "{request}"

For each paragraph, return your response in this exact JSON format:
{{
    "suggestions": [
        {{
            "paragraph_number": 0,
            "has_suggestion": true/false,
            "suggested_text": "improved version of the text",
            "reason": "brief explanation of the change"
        }},
        ...
    ]
}}

Only suggest changes if they meaningfully improve the text. If no changes are needed for a paragraph, set has_suggestion to false for that paragraph.
Process all paragraphs provided and return suggestions for each one."""
                    },
                    {
                        "role": "user",
                        "content": batch_text
                    }
                ],
                temperature=0.3,
                max_tokens=2000,
                response_format={"type": "json_object"}
            )
            
            # Parse AI response
            import json
            ai_response = json.loads(response.choices[0].message.content)
            
            # Extract suggestions for each paragraph in the batch
            batch_suggestions = ai_response.get("suggestions", [])
            
            for suggestion_data in batch_suggestions:
                paragraph_num = suggestion_data.get("paragraph_number", 0)
                
                # Map back to original paragraph index
                if paragraph_num < len(batch):
                    original_idx, original_text = batch[paragraph_num]
                    
                    if suggestion_data.get("has_suggestion", False):
                        suggestions.append({
                            "id": str(uuid.uuid4()),
                            "paragraph_index": original_idx,
                            "original": original_text,
                            "suggested": suggestion_data["suggested_text"],
                            "reason": suggestion_data["reason"],
                        })
        
        except Exception as e:
            # Log error but continue processing other batches
            print(f"Error processing batch starting at {batch_start}: {e}")
            continue
    
    return suggestions


def generate_suggestions_fallback(doc_path: str, request: str) -> list[dict]:
    """Fallback rule-based suggestions if OpenAI API is not available."""
    doc = Document(doc_path)
    suggestions = []
    
    # Simple rule-based suggestions for demonstration
    for idx, paragraph in enumerate(doc.paragraphs):
        if not paragraph.text.strip():
            continue
            
        text = paragraph.text
        
        # Example: Make text more formal
        if "more formal" in request.lower():
            if "don't" in text.lower():
                suggestions.append({
                    "id": str(uuid.uuid4()),
                    "paragraph_index": idx,
                    "original": text,
                    "suggested": text.replace("don't", "do not").replace("Don't", "Do not"),
                    "reason": "Replace contractions with full forms for formality",
                })
        
        # Example: Make text more concise
        if "concise" in request.lower() or "shorter" in request.lower():
            if len(text.split()) > 30:
                suggestions.append({
                    "id": str(uuid.uuid4()),
                    "paragraph_index": idx,
                    "original": text,
                    "suggested": " ".join(text.split()[:20]) + "...",
                    "reason": "Shorten long paragraph for conciseness",
                })
    
    return suggestions


def apply_changes_to_document(doc_path: str, selected_suggestions: list[dict]) -> str:
    """Apply selected suggestions to the document."""
    doc = Document(doc_path)
    
    # Sort suggestions by paragraph index in reverse to avoid index shifting
    sorted_suggestions = sorted(
        selected_suggestions, 
        key=lambda x: x["paragraph_index"], 
        reverse=True
    )
    
    for suggestion in sorted_suggestions:
        idx = suggestion["paragraph_index"]
        if idx < len(doc.paragraphs):
            # Replace paragraph text
            doc.paragraphs[idx].text = suggestion["suggested"]
            
            # Add comment to indicate change (Track Changes simulation)
            # Note: python-docx doesn't support true Track Changes,
            # so we'll add a comment or highlight instead
    
    # Save modified document
    output_path = doc_path.replace(".docx", "_modified.docx")
    doc.save(output_path)
    
    return output_path


@app.list_resources()
async def list_resources() -> list[Resource]:
    """List available resources (the widget)."""
    # Read the built widget HTML
    widget_path = Path("../frontend/dist/index.html")
    
    if widget_path.exists():
        widget_html = widget_path.read_text()
    else:
        # Fallback to a simple HTML if build doesn't exist
        widget_html = """
        <!DOCTYPE html>
        <html>
        <head><title>Document Editor</title></head>
        <body>
            <div id="root">Widget not built yet. Run 'npm run build' in frontend/</div>
        </body>
        </html>
        """
    
    return [
        Resource(
            uri="ui://widget/document-editor.html",
            name="Document Editor Widget",
            mimeType="text/html+skybridge",
            text=widget_html,
        )
    ]


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="upload_document",
            description="Upload a Word document for editing",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Name of the file",
                    },
                    "content": {
                        "type": "string",
                        "description": "Base64 encoded document content",
                    },
                },
                "required": ["filename", "content"],
            },
        ),
        Tool(
            name="analyze_and_suggest",
            description="Analyze document and suggest edits based on user request",
            inputSchema={
                "type": "object",
                "properties": {
                    "doc_id": {
                        "type": "string",
                        "description": "Document ID from upload",
                    },
                    "request": {
                        "type": "string",
                        "description": "User's edit request (e.g., 'make it more formal')",
                    },
                },
                "required": ["doc_id", "request"],
            },
        ),
        Tool(
            name="apply_changes",
            description="Apply selected suggestions to the document",
            inputSchema={
                "type": "object",
                "properties": {
                    "doc_id": {
                        "type": "string",
                        "description": "Document ID",
                    },
                    "suggestion_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of suggestion IDs to apply",
                    },
                },
                "required": ["doc_id", "suggestion_ids"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls."""
    
    if name == "upload_document":
        # Decode and save document
        filename = arguments["filename"]
        content = base64.b64decode(arguments["content"])
        
        doc_id = str(uuid.uuid4())
        doc_path = UPLOAD_DIR / f"{doc_id}.docx"
        
        with open(doc_path, "wb") as f:
            f.write(content)
        
        # Extract metadata
        metadata = extract_document_metadata(str(doc_path))
        
        # Store document info
        documents[doc_id] = {
            "filename": filename,
            "path": str(doc_path),
            "metadata": metadata,
        }
        
        return [
            TextContent(
                type="text",
                text=f"Uploaded document: {filename}\nWord count: {metadata['word_count']}\nParagraphs: {metadata['paragraph_count']}",
            )
        ]
    
    elif name == "analyze_and_suggest":
        doc_id = arguments["doc_id"]
        request = arguments["request"]
        
        if doc_id not in documents:
            return [TextContent(type="text", text="Document not found")]
        
        doc_path = documents[doc_id]["path"]
        suggestions = generate_suggestions(doc_path, request)
        
        # Store suggestions
        suggestions_store[doc_id] = suggestions
        
        # Return structured content for widget
        return [
            TextContent(
                type="text",
                text=f"Found {len(suggestions)} suggestions for: {request}",
                # Add structured content for widget
                annotations={
                    "structuredContent": {
                        "suggestions": suggestions,
                        "doc_id": doc_id,
                    }
                },
            )
        ]
    
    elif name == "apply_changes":
        doc_id = arguments["doc_id"]
        suggestion_ids = arguments["suggestion_ids"]
        
        if doc_id not in documents or doc_id not in suggestions_store:
            return [TextContent(type="text", text="Document or suggestions not found")]
        
        # Get selected suggestions
        all_suggestions = suggestions_store[doc_id]
        selected = [s for s in all_suggestions if s["id"] in suggestion_ids]
        
        # Apply changes
        doc_path = documents[doc_id]["path"]
        modified_path = apply_changes_to_document(doc_path, selected)
        
        # Store modified document path
        documents[doc_id]["modified_path"] = modified_path
        
        return [
            TextContent(
                type="text",
                text=f"Applied {len(selected)} changes to document",
                annotations={
                    "structuredContent": {
                        "download_url": f"/downloads/{os.path.basename(modified_path)}",
                        "applied_count": len(selected),
                    }
                },
            )
        ]
    
    return [TextContent(type="text", text=f"Unknown tool: {name}")]


from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import Route, Mount
from mcp.server.sse import SseServerTransport
import uvicorn

# ... existing code ...

async def handle_sse(request):
    transport = SseServerTransport("/messages")
    async with app.run(transport.read_stream, transport.write_stream, app.create_initialization_options()) as streams:
        await streams
    return await transport.handle_sse(request)

async def handle_messages(request):
    # This would need to be connected to the transport created in handle_sse
    # However, the MCP SDK's SseServerTransport handles this internally if we structure it right
    # For simplicity in this quickstart, we'll try to follow valid MCP SSE patterns
    # But python SDK documentation for SSE is less common than Node.
    
    # Alternative: Use the high-level FastAPI/Starlette integration if available in SDK likely via mcp.server.fastapi?
    # Let's check available moves. The simplest valid SSE implementation:
    pass

# Let's use the standard MCP SSE implementation pattern for Python
from starlette.responses import Response, JSONResponse
from mcp.server.sse import SseServerTransport

sse = SseServerTransport("/messages")

async def handle_sse(scope, receive, send):
    """
    ASGI handler for SSE connections.
    """
    async with sse.connect_sse(scope, receive, send) as streams:
        await app.run(streams[0], streams[1], app.create_initialization_options())

async def handle_messages(scope, receive, send):
    """
    ASGI handler for message posting.
    """
    await sse.handle_post_message(scope, receive, send)

async def handle_root(request):
    return JSONResponse({"status": "healthy", "message": "MCP Server is running"})

# REST API endpoints for standalone testing
from starlette.requests import Request
from starlette.responses import FileResponse

async def handle_upload(request: Request):
    """REST endpoint to upload a document."""
    form = await request.form()
    file = form.get("file")
    
    if not file:
        return JSONResponse({"error": "No file provided"}, status_code=400)
    
    # Read file content
    content = await file.read()
    filename = file.filename
    
    # Create doc_id and save
    doc_id = str(uuid.uuid4())
    doc_path = UPLOAD_DIR / f"{doc_id}.docx"
    
    with open(doc_path, "wb") as f:
        f.write(content)
    
    # Extract metadata
    metadata = extract_document_metadata(str(doc_path))
    
    # Store document info
    documents[doc_id] = {
        "filename": filename,
        "path": str(doc_path),
        "metadata": metadata,
    }
    
    return JSONResponse({
        "doc_id": doc_id,
        "filename": filename,
        "metadata": metadata
    })

async def handle_analyze(request: Request):
    """REST endpoint to analyze document and get suggestions."""
    data = await request.json()
    doc_id = data.get("doc_id")
    edit_request = data.get("request")
    
    if not doc_id or not edit_request:
        return JSONResponse({"error": "Missing doc_id or request"}, status_code=400)
    
    if doc_id not in documents:
        return JSONResponse({"error": "Document not found"}, status_code=404)
    
    doc_path = documents[doc_id]["path"]
    suggestions = generate_suggestions(doc_path, edit_request)
    
    # Store suggestions
    suggestions_store[doc_id] = suggestions
    
    return JSONResponse({
        "doc_id": doc_id,
        "suggestions": suggestions,
        "count": len(suggestions)
    })

async def handle_apply(request: Request):
    """REST endpoint to apply selected suggestions."""
    data = await request.json()
    doc_id = data.get("doc_id")
    suggestion_ids = data.get("suggestion_ids", [])
    
    if not doc_id:
        return JSONResponse({"error": "Missing doc_id"}, status_code=400)
    
    if doc_id not in documents or doc_id not in suggestions_store:
        return JSONResponse({"error": "Document or suggestions not found"}, status_code=404)
    
    # Get selected suggestions
    all_suggestions = suggestions_store[doc_id]
    selected = [s for s in all_suggestions if s["id"] in suggestion_ids]
    
    if not selected:
        return JSONResponse({"error": "No valid suggestions selected"}, status_code=400)
    
    # Apply changes
    doc_path = documents[doc_id]["path"]
    modified_path = apply_changes_to_document(doc_path, selected)
    
    # Create a user-friendly filename based on original filename
    original_filename = documents[doc_id]["filename"]
    # Remove .docx extension if present, add _modified, then add .docx
    base_name = original_filename.rsplit('.', 1)[0] if '.' in original_filename else original_filename
    download_filename = f"{base_name}_modified.docx"
    
    # Store modified document path and download filename
    documents[doc_id]["modified_path"] = modified_path
    documents[doc_id]["download_filename"] = download_filename
    
    return JSONResponse({
        "success": True,
        "applied_count": len(selected),
        "download_url": f"/api/download/{doc_id}"
    })

async def handle_download(request: Request):
    """REST endpoint to download modified document."""
    doc_id = request.path_params.get("doc_id")
    
    if doc_id not in documents:
        return JSONResponse({"error": "Document not found"}, status_code=404)
    
    modified_path = documents[doc_id].get("modified_path")
    if not modified_path or not Path(modified_path).exists():
        return JSONResponse({"error": "Modified document not found"}, status_code=404)
    
    # Use the stored download filename with proper extension
    download_filename = documents[doc_id].get("download_filename", "modified_document.docx")
    
    return FileResponse(
        path=str(modified_path),
        filename=download_filename,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

# Define routes
routes = [
    Route("/", handle_root),
    Route("/api/upload", handle_upload, methods=["POST"]),
    Route("/api/analyze", handle_analyze, methods=["POST"]),
    Route("/api/apply", handle_apply, methods=["POST"]),
    Route("/api/download/{doc_id}", handle_download, methods=["GET"]),
    Mount("/sse/messages", app=handle_messages),
    Mount("/sse", app=handle_sse),
]

# Configure CORS
middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow all origins in development
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )
]

starlette_app = Starlette(debug=True, routes=routes, middleware=middleware)

if __name__ == "__main__":
    uvicorn.run(starlette_app, host="0.0.0.0", port=8787)

