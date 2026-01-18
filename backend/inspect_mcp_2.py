from mcp.server.sse import SseServerTransport
from mcp.server import Server
import inspect

print("Signature of SseServerTransport.connect_sse:")
print(inspect.signature(SseServerTransport.connect_sse))

print("\nSignature of Server.run:")
print(inspect.signature(Server.run))
