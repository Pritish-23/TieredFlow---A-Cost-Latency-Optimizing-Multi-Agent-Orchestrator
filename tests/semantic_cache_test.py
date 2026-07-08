from cache.semantic_cache import SemanticCache

c = SemanticCache()

c.store('What is machine learning?', 'ML is a subset of AI.', 'mid', 0.001)
result = c.lookup('What is machine learning?')

print(result.found)
print(result.similarity_score)
print(result.cached_response)