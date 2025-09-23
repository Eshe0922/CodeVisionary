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

def extract_plan_list(plan):
    lines = plan.strip().split('\n')
    plan_list = []
    
    for line in lines:
        try:
            json_obj = json.loads(line)
            plan_list.append(json_obj)
        except json.JSONDecodeError as e:
            return '', 'Error! Your evaluation plan is not valid JSONL format.'
    print(plan_list)
    return plan_list, ''

class PlanAnalyzer(Agent):
    def __init__(self, sandbox):
        # self.model = "gpt-4o-2024-05-13"
        self.model = "anthropic/claude-3.5-sonnet"
        self.max_turn = 30
        self.temperature = 0.2
        self.max_tokens = 10000
        self.sandbox = sandbox
        self.sandbox_session = self.sandbox.get_session()
        self.tool_lib = [
            Tools.syntax_check,
            Tools.web_browse,
            Tools.screenshot_analyse
        ]
        tools_list = ""
        for idx, tool in enumerate(self.tool_lib):
            tools_list += f"{idx+1}. {tool.value['command']} #\n {tool.value['description']}\n"

        self.init_plan_prompt_EN = f"""\
As an expert in code generation tasks, your mission is to develop an evaluation plan to assess the LLM-generated response for a given code generation task. 
You are currently in a non-GUI Linux environment, where you can use the command line or given external tools for operations. 
You have root privileges and can execute commands directly without using `sudo`.
Each step of the plan should include the goal of the step and the guidance on how to perform it, and should be output in JSONL format.

<Tool List>
In addition to typical bash commands, you can use the following listed commands in your evaluation plan:\n{tools_list} 
</Tool List>

{EDIT_PROMPT}

<Workflow>
1. **Understand the Code Generation Task and the Response**: Carefully read the code generation task and the LLM-generated response.
2. **Break Down Steps**: Decompose the response into individual steps, ensuring each task requirement is evaluated.
3. **Submit Evaluation Plan**: Submit the evaluation plan.(The evaluation plan should not exceed a maximum of 8 steps!)
    In each step of the plan, you can only use the following methods for analysis:
    - **Dynamic Execution Analysis**: Execute the code in the LLM-generated response and analyze the dynamic execution messages. (This step can be optionally skipped for files that cannot be directly executed.)
    - **Static Linter Analysis**: Use the `syntax_check -f 'path'` command to check the code in the LLM-generated response and analyze the linting messages (code syntax, code style, potential errors, etc.). (This step is mandatory.)
    - **Unit Tests Analysis**: Write and execute unit tests for the code in the LLM-generated response and analyze the unit test messages. (Skip this step if the code file has dynamic execution errors or cannot be directly executed.)
    - **Screenshot Analysis**: For HTML files, use the `screenshot_analyse -f 'html_file_path' [-q 'query'] [-a '[actions...]']` command to render it into a screenshot and provide analysis by a software expert. Additionally, you can ask questions. For CSS or JavaScript files, embed them into an HTML file first.
    - **Interaction Analysis**: For HTML files, use the `screenshot_analyse -f 'html_file_path' [-q 'query'] [-a '[actions...]']` command to render it into a screenshot and provide analysis by a software expert. Additionally, you can specify interaction actions before taking the screenshot or ask questions. For CSS or JavaScript files, embed them into an HTML file first.
    - **Web Browsing Analysis**: Use the `web_browse -q 'query'` command to search the web for more comprehensive and professional content to evaluate the response. (This step is helpful when you are unfamiliar with the related content.)
    - **General Semantic Analysis**: The evaluation plan may also include semantic understanding analysis, functionality analysis, complexity analysis, logical correctness analysis, documentation check, natural language comment analysis, etc. These steps do not require external tools but need to be designed and adjusted according to specific situations.
    - **Bash Command**: Additionally, the plan may need to include other steps such as file writing, configuration file changes, data preparation, etc. These steps need to be designed and adjusted according to specific situations.
</Workflow>

<Report Format>
Once you have ensured that the evaluation plan has been developed, please submit the report in the following format:
### Final Report:
{{"step": 0, "goal": "Bash Command", "guidance": "(Combine the code generation task and the response, and explain the specific approach for this step, including the commands to be called)"}}
{{"step": 1, "goal": "Static Linter Analysis", "guidance": "XXX"}}
{{"step": X, "goal": "XXX", "guidance": "XXX"}}
</Report Format>

<Important Tips>
* In each step of the plan, you can only use the following methods for analysis: Dynamic Execution Analysis, Static Linter Analysis, Unit Tests Analysis, Screenshot Analysis, Interaction Analysis, Web Browsing Analysis, General Semantic Analysis, Bash Command.
* You only need to formulate the step-by-step analysis evaluation plan and should not execute any steps!
* The evaluation plan should not exceed a maximum of 6 steps!
</Important Tips>
"""

        self.init_analyse_prompt_EN = f"""\
As an expert in code generation tasks, your mission is to evaluate the LLM-generated response for a given code generation task based on the given evaluation plan. 
You need to execute each step and report the evaluation results for each step.
You are currently in a non-GUI Linux environment, where you can use the command line or given external tools for operations. You have root privileges and can execute commands directly without using `sudo`.

<Tool List>
In addition to typical bash commands, you can use the following listed commands:\n{tools_list} 
</Tool List>

{INIT_PROMPT}

<Tool Usage>
You can call CLI tools in the {BASH_FENCE[0]} ... {BASH_FENCE[1]} block in the form of Action and Thought. For example:
### Thought: I need to run the file and verify the execution message.
### Action:
{BASH_FENCE[0]} 
python a.py
{BASH_FENCE[1]}
</Tool Usage>

{EDIT_PROMPT}

<Workflow>
Your workflow should alternate between the following two steps, i.e., `### State: Execute' and `### State: Analyse' should alternate.
<Step 1> 
Execute a single step based on the evaluation plan and indicate the status as `### State: Execute', for example:
### Thought:
I will follow and execute the current step in the plan.
### Action:
```bash 
python a.py
```
### State: Execute
</Step 1> 

<Step 2> 
Analyze and report the evaluation result of the single step, and indicate the status as `### State: Analyse'. 
You need to use the command `report_single_step' to indicate that you have completed the single step and reported the evaluation result.
Besides, you have to provide the single step report after `### Single Step Report', for example:
### Thought:
I will report the evaluation result of the current step in the plan.
### Action:
```bash 
report_single_step
```
### State: Analyse
### Single Step Report:
{SINGLE_SETP_REPORT}
</Step 2> 

</Workflow>

<Report Format>
Once you have ensured that you have completed the evaluation of the answer, please indicate it as follows:
### Final Report:
I have completed the evaluation of all aspects of the answer!
</Report Format>

<Important Tips>
- You should not modify the code snippets in code generation tasks and LLM generated responses, even if there are syntax errors and bugs in the code snippets or the code snippets cannot run successfully. Your task is to generate the evaluation results of the answer according to the evaluation plan!
- If you have generated all the evaluation results based on the evaluation plan, end the task with reporting `### Final Report'.
- You can only execute one step from the plan or report one step's evaluation result per round. Your workflow should alternate between the Step 1 and Step 2.
- You may take additional steps beyond the given evaluation plan or skip certain evaluation steps based on the actual situation.
</Important Tips>
"""

    def run(self, project_path, item, trajectory, build_report, comprehend_report, args):
        def get_current_files():
            file_list = []
            for root, dirs, files in os.walk(project_path):
                for file in files:
                    file_list.append(os.path.join(root, file))
            return set(file_list)
        
        def trans_screenshot_in_report(report):
            pattern = r'!\[(Screenshot|截图)\]\((.*?)\)'
            
            images_path = []
            
            def replace_path(match):
                image_path = match.group(2)
                file_name = os.path.basename(image_path)
                
                check_command = f'ls {image_path}'
                result = self.sandbox_session.execute(check_command)
                
                if "No such file or directory" in result:
                    find_command = f'find . -name "{file_name}"'
                    find_result = self.sandbox_session.execute(find_command)
                
                    if "###Observation:" in find_result:
                        paths = find_result.split("###Observation:")[1].strip().split("\n")
                        if paths:
                            image_path = paths[0].strip()
                
                images_path.append(image_path)
                
                return f'![{match.group(1)}]({file_name})'

            new_report_content = re.sub(pattern, replace_path, report)
            return new_report_content, images_path


        def code_plan():
            print('******************************************')
            print('************** code plan **************')
            print('******************************************')

            start_time = time.time()
            self.messages = []

            system_message = {"role": "system", "content": self.init_plan_prompt_EN}
            user_message1 = {"role": "user", "content": f"<Code Generation Task>\n{item['query']}\n</Code Generation Task>\n<LLM-generated response>\n{item['answer']}\n</LLM-generated response>\n<Project root Path>{project_path}\n</Project root Path>"}
            user_message2 = {"role": "user", "content": f"<Task Requirements>\n{COMPREHENDER_PROMPT} Here is their report:\n{comprehend_report}\n</Task Requirements>"}
            user_message3 = {"role": "user", "content": f"<Environment Configuration>\n{BUILD_PROMPT}Here is their report: {build_report}\n</Environment Configuration>"}
            self.messages.extend([system_message, user_message1, user_message2, user_message3])

            turn = 0
            cost_tokens = 0
            while(turn < self.max_turn):
                turn += 1
                evaluater_answer, usage = get_llm_response(self.model, self.messages, self.temperature)
                cost_tokens += usage["total_tokens"]

                assistant_message = {"role": "assistant", "content": evaluater_answer}
                self.messages.append(assistant_message)
                print(f'------------- {turn} -------------')
                print(evaluater_answer)
                plan = extract_report(evaluater_answer)
                system_res = '### Observation: \n'
                if plan == None:
                    system_res += """Error! Your response does not include a step-by-step analysis evaluation plan! Additionally, you only need to formulate a step-by-step analysis evaluation plan and should not execute any steps!
Please provide the evaluation plan in the following format, with no more than 8 steps(the evaluation plan is in Jsonl format), for example:

### Report:
{"step": 0, "goal": "Bash Command", "guidance": "(Combine the code generation task and the response, and explain the specific approach for this step, including the commands to be called)"}
{"step": 1, "goal": "Static Linter Analysis", "guidance": "XXX"}
{"step": X, "goal": "XXX", "guidance": "XXX"}
"""
                else:
                    plan_list, plan_list_res = extract_plan_list(plan)
                    if plan_list:
                        break
                    else:
                        system_res += plan_list_res
                system_res += f"\nENVIRONMENT REMINDER: You have {self.max_turn - turn} turns left to complete the task."
                print(system_res)
                
                if "gpt" in self.model:
                    system_message = {"role": "system", "content": system_res}
                else:
                    system_message = {"role": "user", "content": system_res}
                self.messages.append(system_message)
            
            append_trajectory(trajectory, self.messages, 'plan_analyze')
            end_time = time.time()
            cost_time = end_time - start_time
            trajectory.append({'agent': "plan_analyze", 'cost_time': cost_time, 'cost_tokens': cost_tokens}) 
            return plan, plan_list
        
        def code_analyse(plan, plan_list):
            print('******************************************')
            print('************** code analyse **************')
            print('******************************************')
            start_time = time.time()
            self.messages = []
            single_step_reports = []
            system_message = {"role": "system", "content": self.init_analyse_prompt_EN}
            user_message1 = {"role": "user", "content": f"<Code Generation Task>\n{item['query']}\n</Code Generation Task>\n<LLM-generated response>\n{item['answer']}\n</LLM-generated response>\n<Project root Path>{project_path}\n</Project root Path>"}
            user_message2 = {"role": "user", "content": f"<Task Requirements>\n{COMPREHENDER_PROMPT} Here is their report:\n{comprehend_report}\n</Task Requirements>"}
            user_message3 = {"role": "user", "content": f"<Environment Configuration>\n{BUILD_PROMPT}Here is their report: {build_report}\n</Environment Configuration>"}
            user_message4 = {"role": "user", "content": f"<Evaluation Plan>Your colleagues have formulated a complete step-by-step analysis evaluation plan. You should execute each step one by one and report the evaluation results of each step. Here is their step-by-step analysis evaluation plan:\n{plan}</Evaluation Plan>"}
            self.messages.extend([system_message, user_message1, user_message2, user_message3, user_message4])
            
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
                final_report, single_step_report, commands, diffs, system_res = action_check(evaluater_answer, plan_list, 'evaluator')
                system_res += "### Important Tips: Notice that do not modify the code snippets in code generation tasks and LLM generated responses, even if there are syntax errors and bugs in the code snippets or the code snippets cannot run successfully. Your task is to generate the evaluation results of the answer according to the evaluation plan! (This is just a prompt and does not mean that your current action is incorrect.)"
                if final_report:
                    break
                elif single_step_report:
                    single_step_reports.append(single_step_report)
                elif commands: 
                    for i in range(len(commands)):
                        sandbox_res = ''
                        sandbox_res =  self.sandbox_session.execute(commands[i])
                        system_res += sandbox_res
                        if TIME_OUT_LABEL in sandbox_res:
                            self.sandbox_session =  self.sandbox.get_session()
                elif diffs:
                    tmp_name = save_diff_description(diffs)
                    sandbox_res =  self.sandbox_session.edit(tmp_name, project_path)
                    system_res += sandbox_res
                    if TIME_OUT_LABEL in sandbox_res:
                        self.sandbox_session =  self.sandbox.get_session()

                system_res += f"\nENVIRONMENT REMINDER: You have {self.max_turn - turn} turns left to complete the task."
                print(system_res)
                
                if "gpt" in self.model:
                    system_message = {"role": "system", "content": system_res}
                else:
                    system_message = {"role": "user", "content": system_res}
                self.messages.append(system_message)
            
            report = '# Stepwise Evaluation Results\n' + '\n'.join(single_step_reports)

            def update_steps(input_string):
                pattern = re.compile(r'## Step (\d+):')
                step_counter = 0
                
                def replace_step(match):
                    nonlocal step_counter
                    replacement = f"## Step {step_counter}:"
                    step_counter += 1
                    return replacement
                
                updated_string = pattern.sub(replace_step, input_string)
                
                return updated_string
            
            report = update_steps(report)
            report, images_path = trans_screenshot_in_report(report)
            append_trajectory(trajectory, self.messages, 'plan_analyze')
            end_time = time.time()
            cost_time = end_time - start_time
            trajectory.append({'agent': "plan_analyze", 'cost_time': cost_time, 'cost_tokens': cost_tokens}) 
            return trajectory, report, single_step_reports, images_path
        
        all_retry = 3
        plan, plan_list = code_plan()

        for retry in range(all_retry):
            initial_files = get_current_files()   
            trajectory, report, single_step_reports, images_path = code_analyse(plan, plan_list)
            if len(single_step_reports) > 3 and report:
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

        return trajectory, report.strip(), single_step_reports, images_path
        


