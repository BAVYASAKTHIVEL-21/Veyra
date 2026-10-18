import json
from backend.agent.investigator import (
    list_scenarios,
    investigate_scenario,
)

print("Available scenarios:")
print(json.dumps(list_scenarios(), indent=2, default=str))

print("\nRunning scenario_001:")
report = investigate_scenario("scenario_001")
print(json.dumps(report, indent=2, default=str))

print("\nTesting an unknown scenario:")
print(json.dumps(
    investigate_scenario("scenario_999"),
    indent=2,
    default=str,
))
