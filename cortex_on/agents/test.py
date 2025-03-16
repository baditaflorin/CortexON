
from typing import List, Dict, Any
from code_agent import coder_agent
import logfire
import os
from planner_agent import planner_agent
from orchestrator_agent import orchestrator_agent

print(f"LOGFIRE_TOKEN: {os.getenv('LOGFIRE_TOKEN')}")

logfire.configure(
            send_to_logfire='if-token-present',
            token=os.getenv("LOGFIRE_TOKEN"),
            scrubbing=False,
)

result =  orchestrator_agent.run_sync(
    user_prompt="What is the price of rtx 3050 on amazon gather 5-6 sample prices? after you get the prices write and execute a python script to get the average price of the rtx 3050 ",
)

print(result.data)