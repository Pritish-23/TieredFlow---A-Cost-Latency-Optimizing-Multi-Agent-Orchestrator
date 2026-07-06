from providers.groq_provider import GroqProvider

p = GroqProvider('llama-3.1-8b-instant')

print(p.is_available())

r = p.call('Say hello in one sentence.')

print(r.content)
print(r.latency_ms)