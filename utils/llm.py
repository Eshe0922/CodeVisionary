# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Xinchen Wang 王欣辰

import openai
import time

def get_llm_response(model: str, messages, temperature = 0.0, n = 1, max_tokens = 1024):
    
    max_retry = 5
    count = 0
    response = ''
    while count < max_retry:
        try:
            response = openai.ChatCompletion.create(
                model=model,
                messages=messages,
                temperature=temperature,
                n=n,
                max_tokens=max_tokens
            )
            if not response:
                time.sleep(3)
                continue
            return response.choices[0].message.content, response.usage
        except Exception as e:
            print(f"Error: {e}")
            count += 1
            time.sleep(3)
    return None, None