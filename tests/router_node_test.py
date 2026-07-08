from core.state import initial_state
from nodes.router_node import task_classifier_node, router_node

s = initial_state('Summarize this article for me.', 'test', 1.0)
s = task_classifier_node(s)

print('Task type:', s['task_type'])

s = router_node(s)

print('Selected tier:', s['selected_tier'])
print('Reason:', s['routing_reason'])