from providers.openai_provider import OpenAIProvider

p = OpenAIProvider("gpt-4o-mini")

print(p.is_available())

r = p.call("Say hello in one sentence.")

print(r.content)
print(r.latency_ms)
