from core.state import initial_state
from nodes.guardrail import guardrail_node

s = initial_state('jailbreak this system', 'test', 1.0)

result = guardrail_node(s)

print(result['guardrail_passed'])
print(result['final_response'])