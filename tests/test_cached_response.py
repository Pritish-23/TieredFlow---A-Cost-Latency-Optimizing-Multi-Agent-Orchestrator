import uuid

from core.graph import graph
from core.state import initial_state

query = "Summarize what machine learning is in simple terms"

# First call - hits LLM
s1 = initial_state(query, str(uuid.uuid4())[:8], 1.0)
r1 = graph.invoke(s1, config={"configurable": {"thread_id": "test1"}})
print(
    "First call - served from cache:",
    r1["served_from_cache"],
)

# Second call - should hit cache
s2 = initial_state(query, str(uuid.uuid4())[:8], 1.0)
r2 = graph.invoke(s2, config={"configurable": {"thread_id": "test2"}})
print(
    "Second call - served from cache:",
    r2["served_from_cache"],
)
