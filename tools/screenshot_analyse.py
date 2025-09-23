# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Xinchen Wang 王欣辰

import os, sys
import subprocess
import argparse
import shutil
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
from utils.llm import get_llm_response
import base64
import json
def image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        base64_encoded = base64.b64encode(image_file.read()).decode('utf-8')
    return base64_encoded

def screen_shot_analyse(path, query = None, actions = None):
    base, ext = os.path.splitext(path)
    path1 = base + '.png'

    i = 1  
    new_path1 = path1

    while os.path.exists(new_path1):
        new_path1 = f"{base}_{i}.png"
        i += 1

    path1 = new_path1
    print(f"The path of the screenshot is {path1}")

    actions_list = []
    if actions:
        try:
            actions_list = json.loads(actions)
        except json.JSONDecodeError as e:
            print(f"Error parsing actions: {e}")
            exit(1)

    command = ['node', '/home/tools/screenshot_puppeteer_interact.js', path, path1] + actions_list

    output = subprocess.run(command, capture_output=True, text=True)
    base64_image = image_to_base64(path1)
    prompt = """
You are an expert in software engineering and code analysis. Please analyze the following screenshot rendered by front-end code and provide insights on the following aspects:

1. Component Information:
Identify all front-end components in the image and describe the function of each component.

2. Component Interaction:
Analyze the potential interactions between components and describe the events and behaviors associated with these interactions.
"""
    if actions_list:
        prompt += f"""
3. Actions Analysis:
We have performed the actions listed in actions_list. Analyze the provided actions and describe their effects on the components.
The actions are: {actions_list}
"""
    if query:
        prompt += f"""
4. Answer User Query:
Address the specific question provided by the user with detailed explanations.
User Query: {query}
"""
 
    messages= [{"role": "user", "content": [{"type": "image_url","image_url":{"url": base64_image}},{"type": "text","text": f"{prompt}"}]}]
    answer, _ = get_llm_response("aws_claude35_sdk_sonnet_v2", messages)
    print(answer)
    return answer

def main():

    parser = argparse.ArgumentParser(description="Run frontend rendering on files.")
    parser.add_argument("-f", type=str, required=True, help="Path to the file or directory") 
    parser.add_argument("-q", type=str, default=None, help="User Question")   
    parser.add_argument('-a', type=str, help='JSON formatted list of actions to perform')
    args = parser.parse_args()
    output_info = screen_shot_analyse(args.f, args.q, args.a)
    return output_info
    

if __name__ == "__main__":
    main()