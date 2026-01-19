import asyncio
import logging
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client

# logging.basicConfig(level=logging.DEBUG)

async def test_live_connection():
    sse_url = "https://beata-discriminantal-sirena.ngrok-free.dev/sse"
    print(f"🔌 Connecting to {sse_url} ...")
    try:
        async with sse_client(sse_url) as (read_stream, write_stream):
            print("✅ Transport Connected!")
            async with ClientSession(read_stream, write_stream) as session:
                print("🔄 Initializing Session...")
                await session.initialize()
                print("✅ Session Initialized!")
                print("📨 Sending 'list_tools' request...")
                tools = await session.list_tools()
                print(f"🎉 Received Response: Found {len(tools.tools)} tools")
                for tool in tools.tools:
                    print(f"   - 🛠️  {tool.name}")
                
                print("📨 Sending 'call_tool' (upload_document) request...")
                
                # Create a dummy docx in memory
                import io, base64
                from docx import Document as DocxDocument
                
                doc = DocxDocument()
                doc.add_paragraph("Test document content.")
                bio = io.BytesIO()
                doc.save(bio)
                bio.seek(0)
                b64_content = base64.b64encode(bio.read()).decode('utf-8')
                
                try:
                    result = await session.call_tool("upload_document", arguments={
                        "filename": "test_verification.docx",
                        "content": b64_content
                    })
                    print(f"🎉 Tool Call Success!")
                    for content in result.content:
                        if content.type == "text":
                            print(f"   Text: {content.text}")
                            if hasattr(content, "annotations"):
                                print(f"   Annotations: {content.annotations}")
                            else:
                                print(f"   WARNING: No annotations found on content object!")
                except Exception as e:
                    print(f"❌ Tool Call Failed: {e}")

                return True
    except Exception as e:
        print(f"❌ Connection Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(test_live_connection())
