from providers import get_provider

from config.constants import Tier

p = get_provider(Tier.ULTRA_CHEAP)

r = p.call('Say hello in one sentence.')

print(r.provider)
print(r.model_id)
print(r.latency_ms)