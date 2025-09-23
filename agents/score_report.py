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
import base64
import copy

def extract_and_write_scores(answer):
    item = {}

    match = re.search(r'Overall Score:\s*(\d+)', answer)
    if match:
        score = match.group(1)
        item['evaluation_score'] = float(score)
    else:
        item['evaluation_score'] = None

    if 'Overall Evaluation Reason:' in answer:
        reason = answer.split('Overall Evaluation Reason:', 1)[1].strip()  
        item['evaluation_reason'] = reason
    else:
        item['evaluation_reason'] = None

    return item

class LLMAgent:
    def __init__(self, model, temperature):
        self.model = model
        self.temperature = temperature
        self.messages = []
        self.current_message = None
        self.index = None
        self.scores = None

    def evaluate(self):
        response, _ = get_llm_response(self.model, self.messages, self.temperature)
        return response

    def set_scores(self, scores):
        self.scores = scores

def extract_final_scores(agents):

    scores_per = []
    score = 0
    num = 0

    print('*******************************')
    for idx, agent in enumerate(agents):
        scores_per.append(agent.scores['evaluation_score'])
        if agent.scores['evaluation_score'] != None:
            score += agent.scores['evaluation_score']
            num += 1

    final_score = score/num
    return final_score, scores_per
    
class ScoreReporter(Agent):
    def __init__(self, sandbox, args):
        self.model = "gpt-4o-2024-05-13"
        # self.model = "aws_claude35_sonnet"
        self.temperature = 0.7
        self.sample_num = 3
        self.max_turn = 5
        self.sandbox = sandbox
        self.init_prompt = REPORT_PROMPT
        self.agents = [LLMAgent(self.model, self.temperature) for _ in range(self.sample_num)]
        for agent in self.agents:
            agent.index = self.agents.index(agent)

    def run(self, project_path, item, trajectory, build_report, comprehend_report, specialized_report, args):

        def run_first():
            messages = []
            system_message = {"role": "system", "content": self.init_prompt}
            user_message1 = {"role": "user", "content": f"<Code Generation Task>\n{item['query']}\n</Code Generation Task>\n<LLM-generated response>\n{item['answer']}\n</LLM-generated response>\n"}
            user_message2 = {"role": "user", "content": f"<Task Requirements>\n{COMPREHENDER_PROMPT} Your evaluation should consider all the task requirements. Here is their report:\n{comprehend_report}\n</Task Requirements>"}
            user_message3 = {"role": "user", "content": f"<Stepwise Evaluation Results>\nYour colleagues have analyzed the LLM-generated response and collected multisource domain konwledge from different aspects, your can consider the conclusion from it. Notice that you need to discern carefully about the stepwise evaluation results, as they may contain inaccuracies or invalid evaluations! Here is their evaluation report: \n{specialized_report}\n</Stepwise Evaluation Results>"}
            messages.extend([system_message, user_message1, user_message2, user_message3])
            
            print('***********RUN FIRST***********')

            for idx, agent in enumerate(self.agents):
                print(f'***********{idx}***********')
                agent.messages = copy.deepcopy(messages)
                response = agent.evaluate()
                print(response)
                
                scores = extract_and_write_scores(response)
                agent.set_scores(scores)
                print(agent.scores)

                message = "I have evaluated the answer and my initial overall score and evaluation reason is as follows:\n"
                message += f'Overall Score: {agent.scores["evaluation_score"]}\n'
                message += f'Evaluation Reason: \n{agent.scores["evaluation_reason"]}\n'
                self_message = {"role": "assistant", "content": message}
                agent.messages.append(self_message)
                
                self_message = {"role": "user", "content": REPORT_PROMPT_COMPETE  + f"<Role Description>\n You are the {agent.index}th collaborator! \n</Role Description>"}
                agent.messages.append(self_message)

            for agent in self.agents:
                response = '###Observation: \n'
                for other_agent in self.agents:
                    if other_agent.index != agent.index:
                        response += f'<Current evaluation of the {other_agent.index}th collaborator>\n'
                        response += f'The initial overall score and evaluation reason of the {other_agent.index}th collaborator are as follows:\n'
                        response += f'Overall Score: {other_agent.scores["evaluation_score"]}\n'
                        response += f'Evaluation Reason: \n{other_agent.scores["evaluation_reason"]}\n'
                        response += f'</Current evaluation of the {other_agent.index}th collaborator>\n'
                agent.messages.append({"role": "user", "content": response})

            initial_score, scores_per = extract_final_scores(self.agents)
            return initial_score

        def run_discuss():
            def extract_actions(message):
                actions = re.findall(r'### Action:\s*(.*?)\s*(?=###|$)', message, re.DOTALL)
                return actions if actions else None
            
            inter_scores_list = []
            inter_scores_per_list = []
            for turn in range(self.max_turn):
                print('***********RUN DISCUSS***********')
                print(f'**********************{turn}**********************')
                same_flag = True
                maintain_flag = True

                inter_score, scores_per = extract_final_scores(self.agents)
                inter_scores_list.append(inter_score)
                inter_scores_per_list.append(scores_per)

                for idx, agent in enumerate(self.agents):
                    print(f'***********{idx}***********')
                    response = agent.evaluate()
                    print(response)
                    agent.current_message = response
                
                for idx, agent in enumerate(self.agents):
                    print(f'***********{idx}***********')
                    actions = extract_actions(agent.current_message)

                    print(actions)
                    if not actions:
                        continue
                    for action in actions:
                        if action.startswith("Maintain"):
                            continue
                        elif action.startswith("Change"):
                            maintain_flag = False
                            parts = action.split()
                            evaluation_score = float(parts[1])
                            evaluation_reason = " ".join(parts[2:])
                            scores = {'evaluation_score': evaluation_score, 'evaluation_reason': evaluation_reason}
                            agent.set_scores(scores)
                        elif action.startswith("Agree"):
                            parts = action.split()
                            critiqued_agent_id = int(parts[1])
                            agree_content = " ".join(parts[2:])
                            critiqued_agent = self.agents[critiqued_agent_id]
                            critiqued_agent.messages.append({
                                "role": "user",
                                "content": f"### Observation: The {agent.index}th collaborator agreed with your score and reasoning. The agreement content is as follows: {agree_content}"
                            })
                        elif action.startswith("Query"):
                            maintain_flag = False
                            parts = action.split()
                            critiqued_agent_id = int(parts[1])
                            query_content = " ".join(parts[2:])
                            critiqued_agent = self.agents[critiqued_agent_id]
                            critiqued_agent.messages.append({
                                "role": "user",
                                "content": f"### Observation: The {agent.index}th collaborator requested clarification or further justification for your score. Please carefully consider their query and decide whether to maintain or change your score. The query content is as follows: {query_content}"
                            })
                        elif action.startswith("Disagree"):
                            maintain_flag = False
                            parts = action.split()
                            critiqued_agent_id = int(parts[1])
                            disagree_content = " ".join(parts[2:])
                            critiqued_agent = self.agents[critiqued_agent_id]
                            critiqued_agent.messages.append({
                                "role": "user",
                                "content": f"### Observation: The {agent.index}th collaborator disagreed with your score and reasoning. Please carefully review their disagreement and consider whether to maintain or change your score. The disagreement content is as follows: {disagree_content}"
                            })
                        elif action.startswith("Withdraw"):
                            continue

                        print(agent.scores)

                evaluation_scores = []
                for idx, agent in enumerate(self.agents):
                    evaluation_scores.append(float(agent.scores['evaluation_score']))

                print(evaluation_scores)
                if len(set(evaluation_scores)) > 1:  
                    same_flag = False

                if same_flag or maintain_flag:
                    break

                for idx, agent in enumerate(self.agents):
                    message = f"This is {turn}th round  of the negotiation process. Up to this round, my current overall score and evaluation reason is as follows:\n"
                    message += f'Overall Score: {agent.scores["evaluation_score"]}\n'
                    message += f'Evaluation Reason: \n{agent.scores["evaluation_reason"]}\n'
                    message += f'Besides, I have performed the actions in this round: {agent.current_message}\n'
                    self_message = {"role": "assistant", "content": message}
                    agent.messages.append(self_message)
                    
                for agent in self.agents:
                    response = f'###Observation: \nThis is {turn}th round  of the negotiation process.\n'
                    for other_agent in self.agents:
                        if other_agent.index != agent.index:
                            response += f'<Current evaluation of the {other_agent.index}th collaborator>\n'
                            response += f'Up to this round, the overall score and evaluation reason of the {other_agent.index}th collaborator are as follows: \n'
                            response += f'Overall Score: {other_agent.scores["evaluation_score"]}\n'
                            response += f'Evaluation Reason: \n{other_agent.scores["evaluation_reason"]}\n'
                            response += f'</Current evaluation of the {other_agent.index}th collaborator>\n'
                            response += f'Besides, the {other_agent.index}th collaborator performed the actions: {other_agent.current_message}\n'
                    agent.messages.append({"role": "user", "content": response})

            final_score, scores_per = extract_final_scores(self.agents)
            inter_scores_list.append(final_score)
            inter_scores_per_list.append(scores_per)
            return final_score, inter_scores_list, inter_scores_per_list

        def run_reason(final_score):
            messages = []
            system_message = {"role": "system", "content": REASON_PROMPT}
            user_message1 = {"role": "user", "content": f"<Code Generation Task>\n{item['query']}\n</Code Generation Task>\n<LLM-generated response>\n{item['answer']}\n</LLM-generated response>"}
            user_message2 =  {"role": "user", "content": f"After discussion and negotiation between collaborators, the overall evaluation score is {final_score}"}
            response = "Below are the evaluation reasons of different collaborators: \n"
            for agent in self.agents:
                response += f'<The {agent.index}th collaborator>\n'
                response += f'{agent.scores["evaluation_reason"]}\n'
                response += f'</The {agent.index}th collaborator>\n'
            user_message3 =  {"role": "user", "content": response}

            messages.extend([system_message, user_message1, user_message2, user_message3])
            evaluater_answer, usage = get_llm_response(self.model, messages)
            report = evaluater_answer.strip()
            return report
        
        initial_score = run_first()
        final_score, inter_scores_list, inter_scores_per_list = run_discuss()
        overall_report = run_reason(final_score)
        return trajectory, final_score, overall_report, inter_scores_list, inter_scores_per_list

    
