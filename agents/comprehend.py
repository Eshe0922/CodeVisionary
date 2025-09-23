# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Xinchen Wang 王欣辰

import os, sys
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
from agents.agent import Agent
from utils.llm import get_llm_response
from utils.agent_util import *
from utils.tools_config import Tools
import time
from enum import Enum
from datetime import datetime
import traceback

class Comprehender(Agent):
    def __init__(self, sandbox):
        self.model = "gpt-4o-2024-05-13"
        # self.model = "aws_claude35_sonnet"
        self.temperature = 0.2
        self.max_turn = 10
        self.sandbox = sandbox
        self.init_prompt_EN = f"""\
As an expert in code generation tasks, your mission is to first extract the overall requirements of the given code generation task and then break them down into detailed specific requirements.

<Workflow>
1. **Extract Overall Requirements**:
    - Analyze the task to determine the overall requirements.
2. **Break Down Specific Requirements**:
    - Decompose the main requirements of the task into detailed specific requirements.
    - Explain each specific requirement point by point, ensuring that each specific requirement is clear.
</Workflow>

<Important Tips>
* You should not answer the code generation task.
* Your response should not include the original code generation task.
* Specific requirements should be concise and clear, limited to no more than 6 points.
</Important Tips>

<Report Format>
Once you have ensured that the overall requirements of the task have been extracted and broken down into detailed specific requirements, please submit the report in the following format:
### Final Report: 
{COMPREHENDER_REPORT}
</Report Format>
"""
    
    def run(self, project_path, item, trajectory, args):
        print('******************************************')
        print('************** comprehender **************')
        print('******************************************')
        start_time = time.time()
        self.messages = []
        system_message = {"role": "system", "content": self.init_prompt_EN}
        user_message = {"role": "user", "content": f"<Code Generation Task>\n{item['query']}\n</Code Generation Task>"}
        self.messages.extend([system_message, user_message])

        turn = 0
        cost_tokens = 0
        while(turn < self.max_turn):
            turn += 1
            evaluater_answer, usage = get_llm_response(self.model, self.messages, self.temperature)
            print(f'------------- {turn} -------------')
            print(evaluater_answer)
            cost_tokens += usage["total_tokens"]
            assistant_message = {"role": "assistant", "content": evaluater_answer}
            self.messages.append(assistant_message)
            system_res = ''
            report = extract_report(evaluater_answer)
            if report == None:
                system_res += "### Observation:\nERROR! Your reply does not contain the final report!\n"
            else:
                break
            system_res += f"### Observation:\nENVIRONMENT REMINDER: You have {self.max_turn - turn} turns left to complete the task."
            print(system_res)
            
            if "gpt" in self.model:
                system_message = {"role": "system", "content": system_res}
            else:
                system_message = {"role": "user", "content": system_res}
            self.messages.append(system_message)
    
        append_trajectory(trajectory, self.messages, 'comprehender')
        end_time = time.time()
        cost_time = end_time - start_time
        trajectory.append({'agent': "comprehender", 'cost_time': cost_time, 'cost_tokens': cost_tokens}) 

        report = report.strip()
        now = datetime.now()
        datetime_str = now.strftime('%Y%m%d%H%M%S')
        print("time: ", datetime_str)
        return trajectory, report
        

