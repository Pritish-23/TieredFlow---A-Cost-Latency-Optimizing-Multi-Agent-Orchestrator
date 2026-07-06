from providers.anthropic_provider import AnthropicProvider

p = AnthropicProvider("claude-haiku-4-5-20251001")

print(p.is_available())

r = p.call("Say hello in one sentence.")

print(r.content)
print(r.latency_ms)
print(r.provider)
exit()
