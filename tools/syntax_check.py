# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Xinchen Wang 王欣辰

#!/usr/bin/env python3
import subprocess
import argparse
import os
import shutil

def linter_syntax_check(path, container_name):
    dest_path = '/home/syntax_check_tmp'
    if os.path.isfile(path):
        if not os.path.exists(dest_path):
            os.makedirs(dest_path)
        shutil.copy(path, dest_path)
    elif os.path.isdir(path):
        if os.path.exists(dest_path):
            shutil.rmtree(dest_path)
        shutil.copytree(path, dest_path)
    else:
        raise ValueError("The path is not correct!")

    docker_command = [
        'docker', 'run', '--rm',
        '-v', '/var/run/docker.sock:/var/run/docker.sock:rw',
        '--entrypoint', '/script.sh',
        'codevisionary.lint',
        container_name, '/home/syntax_check_tmp'
    ]

    result = subprocess.run(docker_command, capture_output=True, text=True)
    logs_dir = '/home/syntax_check_tmp/lint/megalinter-reports/linters_logs'
    output_info = []

    if not os.path.exists(logs_dir):
        return result.stdout

    for filename in os.listdir(logs_dir):
        if filename.endswith('.log'):
            error_type = filename.split('-')[0]
            linter_name = filename.split('_')[-1].split('.log')[0]
            log_file_path = os.path.join(logs_dir, filename)
            with open(log_file_path, 'r') as file:
                log_content = file.read()
            output_info.append(f"Syntax Check Type: {error_type}\nSyntax Check Linter: {linter_name}\nSyntax Check Message:\n{log_content}\n")
    delete_command = 'rm -rf /home/syntax_check_tmp'
    subprocess.run(delete_command.split(), capture_output=True, text=True)
    return "\n".join(output_info)
    

def main():
    parser = argparse.ArgumentParser(description="Run syntax check on files.")
    parser.add_argument("-f", type=str, required=True, help="Path to the file or directory")
    parser.add_argument("-c", type=str, required=True, help="The name of the first container")    
    args = parser.parse_args()
    output_info = linter_syntax_check(args.f, args.c)
    print(output_info)
    return output_info

if __name__ == "__main__":
    main()