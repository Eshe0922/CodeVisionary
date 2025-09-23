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
from datetime import datetime
import shutil
import traceback

class Constructor(Agent):
    def __init__(self, sandbox):
        self.model = "gpt-4o-2024-05-13"
        # self.model = "aws_claude35_sonnet"
        self.temperature = 0.2
        self.max_tokens = 20000
        self.max_turn = 30
        self.sandbox = sandbox
        self.sandbox_session = self.sandbox.get_session()
        self.init_plan_prompt_EN = f"""\
Act as a software environment constructor, your task is to create a build plan for setting up a complete environment based on the given code generation task and LLM-generated response. 
You are currently in a non-GUI Linux environment and can perform operations using the command line or the provided external commands. 
You have root privileges and can execute commands directly without using `sudo'. Miniconda3, GCC, NODE are already configured.

<Build Plan>
The build plan might include the following steps:
0. **Code Placement:** 
   - Write the code snippets from the code generation task and LLM-generated response into the appropriate files. Do not modify the code snippets from the code generation task and LLM-generated response. 
1. **Programming Environment:**
   - Specify the programming language and version to be used.
2. **Dependencies:** (not necessarily)
   - List the libraries, frameworks, and tools that need to be installed.
3. **Configuration Files:** (not necessarily)
   - Describe any configuration files that need to be created or modified.
4. **Environment Variables:** (not necessarily)
   - List any environment variables that need to be set.
5. **Verification:**
   - Provide general commands or methods to verify that the environment has been set up correctly.
6. **Others:** (not necessarily)
    - Include any additional steps necessary for the environment setup.
</Build Plan>

<Report Format>
If you have ensured that you have created the build plan, please submit the report in the following format:
### Final Report: 
# Build Plan
    - [Step 1] [Explanation 1]
    - [Step 2] [Explanation 2]
    - [Step X] [Explanation X]
</Report Format>

<Important Tips>
* The plan should be direct, minimal, and executable without redundant steps. 
* Do not answer the code generation task. Your only task is to create a build plan.
* Do not modify the code snippets in the given code generation tasks and LLM-generated responses, even if there are syntax errors in the code snippets or the code snippets cannot run successfully.
</Important Tips>
"""
         
        self.init_configure_prompt_EN = f"""\
You have created the build plan based on the given code generation task and LLM-generated response, and now your task is to construct a complete environment based on your build plan.   
You are currently in a non-GUI Linux environment and can perform operations using the command line or the provided external commands. 
You have root privileges and can execute commands directly without using `sudo`. Miniconda3, GCC, NODE are already configured.

<Workflow>
1. **Configure the environment according to the build plan**:
   - Set up the environment according to each step in the build plan.
2. **Handle non-executable build plans**:
   - If any step fails, identify the issue and attempt alternative methods.
</Workflow>

{INIT_PROMPT}

<Tool Usage>
You can invoke CLI tools in {BASH_FENCE[0]} ... {BASH_FENCE[1]} blocks in the form of Action and Thought. For example:
### Thought: I need to install the latest version of XXX and set up a virtual environment.
### Action:
{BASH_FENCE[0]} 
apt install XXX
{BASH_FENCE[1]}
</Tool Usage>

{EDIT_PROMPT}

<Report Format>
If you have ensured that the environment has been fully configured according to the build plan, please submit the report in the following format:
### Final Report:
{BUILD_REPORT}
</Report Format>

<Important Tips>
* All file changes must use the {DIFF_FENCE[0]} ... {DIFF_FENCE[1]} block format and use the symbols {HEAD}, {DIVIDER}, and {UPDATED}!
* In the `### Final Report:', for any environment setup steps involving file writing, you must specify the file path and the code snippets being written.
* Do not answer the code generation task. Your only task is to configure the environment.
* Do not modify the code snippets in the given code generation tasks and LLM-generated responses, even if there are syntax errors or bugs in the code snippets or the code snippets cannot run successfully.
</Important Tips>
"""
    
    def run(self, project_path, item, trajectory, comprehend_report, args):
        def get_current_files():
            file_list = []
            for root, dirs, files in os.walk(project_path):
                for file in files:
                    file_list.append(os.path.join(root, file))
            return set(file_list)
    
        def build_plan():
            print('******************************************')
            print('************** constructor plan **************')
            print('******************************************')
            start_time = time.time()
            self.messages = []
            system_message = {"role": "system", "content": self.init_plan_prompt_EN}
            user_message1 = {"role": "user", "content": f"<Code Generation Task>\n{item['query']}\n</Code Generation Task>\n<LLM-generated response>\n{item['answer']}\n</LLM-generated response>\n<Project root Path>{project_path}\n</Project root Path>"}
            user_message2 = {"role": "user", "content": f"<Task Requirements>\n{COMPREHENDER_PROMPT} Here is their report:\n{comprehend_report}\n</Task Requirements>"}
            self.messages.extend([system_message, user_message1, user_message2])

            turn = 0
            cost_tokens = 0
            while(turn < self.max_turn):
                turn += 1
                evaluater_answer, usage = get_llm_response(self.model, self.messages, self.temperature, self.max_tokens)
                cost_tokens += usage["total_tokens"]
                assistant_message = {"role": "assistant", "content": evaluater_answer}
                self.messages.append(assistant_message)
                print(f'------------- {turn} -------------')
                print(evaluater_answer)
                plan = extract_report(evaluater_answer)
                system_res = '### Important Tips: Notice that do not modify code snippets in code generation tasks and LLM generated responses. Even if there are syntax errors or bugs in the code snippets or the code snippets cannot run successfully.'
                if plan == None:
                    system_res += "### Observation:\nERROR! Your reply does not contain the final report!\n"
                else:
                    break
                system_res += f"### Observation:\nENVIRONMENT REMINDER: You have {self.max_turn - turn} turns left to complete the task.\n"
                print(system_res)

                if "gpt" in self.model:
                    system_message = {"role": "system", "content": system_res}
                else:
                    system_message = {"role": "user", "content": system_res}
                self.messages.append(system_message)
            
            append_trajectory(trajectory, self.messages, 'constructor')
            end_time = time.time()
            cost_time = end_time - start_time
            trajectory.append({'agent': "constructor", 'cost_time': cost_time, 'cost_tokens': cost_tokens}) 
            return plan

        def build_configure():
            print('******************************************')
            print('************ constructor configure ***********')
            print('******************************************')
            start_time = time.time()
            system_message = {"role": "user", "content": self.init_configure_prompt_EN}
            self.messages.append(system_message)
                
            turn = 0
            cost_tokens = 0
            while(turn < self.max_turn):
                turn += 1
                evaluater_answer, usage = get_llm_response(self.model, self.messages, self.temperature, self.max_tokens)
                cost_tokens += usage["total_tokens"]
                assistant_message = {"role": "assistant", "content": evaluater_answer}
                self.messages.append(assistant_message)
                print(f'------------- {turn} -------------')
                print(evaluater_answer)
                report, _, commands, diffs, system_res = action_check(evaluater_answer)
                system_res += '### Important Tips: Notice that do not modify code snippets in code generation tasks and LLM generated responses, even if there are syntax errors or bugs in the code snippets or the code snippets cannot run successfully. Your only task is to configure the environment. (This is just a prompt and does not mean that your current action is incorrect.)'
                if report:
                    break
                elif commands:
                    for i in range(len(commands)):
                        sandbox_res = ''
                        sandbox_res =  self.sandbox_session.execute(commands[i], timeout = 240, type = False)
                        system_res += sandbox_res
                        if TIME_OUT_LABEL in sandbox_res:
                            self.sandbox_session =  self.sandbox.get_session()
                elif diffs:
                    tmp_name = save_diff_description(diffs)
                    sandbox_res =  self.sandbox_session.edit(tmp_name, project_path)
                    system_res += sandbox_res
                    if TIME_OUT_LABEL in sandbox_res:
                        self.sandbox_session =  self.sandbox.get_session()

                system_res += f"### Observation:\nENVIRONMENT REMINDER: You have {self.max_turn - turn} turns left to complete the task."
                print(system_res)
                
                if "gpt" in self.model:
                    system_message = {"role": "system", "content": system_res}
                else:
                    system_message = {"role": "user", "content": system_res}
                self.messages.append(system_message)
            
            append_trajectory(trajectory, self.messages, 'constructor')
            end_time = time.time()
            cost_time = end_time - start_time
            trajectory.append({'agent': "constructor", 'cost_time': cost_time, 'cost_tokens': cost_tokens}) 
            return trajectory, report
        
        for retry in range(5):
            initial_files = get_current_files()   
            plan = build_plan()
            trajectory, report = build_configure()
            if report:
                break
            else:
                current_files = get_current_files()
                new_files = current_files - initial_files
                for file in new_files:
                    if os.path.isfile(file):
                        os.remove(file)
                    elif os.path.isdir(file):
                        shutil.rmtree(file)
                self.sandbox_session.close()
                self.sandbox_session = self.sandbox.get_session()
        self.sandbox_session.close()
        now = datetime.now()
        datetime_str = now.strftime('%Y%m%d%H%M%S')
        print("time: ", datetime_str)
        return trajectory, report.strip()

