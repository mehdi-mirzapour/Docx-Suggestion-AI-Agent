from mcp.server.sse import SseServerTransport
import inspect

print("Attributes of SseServerTransport:")
for name in dir(SseServerTransport):
    if not name.startswith("_"):
        print(name)

print("\nMethod signatures:")
print(inspect.signature(SseServerTransport.__init__))
