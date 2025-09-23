# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Xinchen Wang 王欣辰

import docker
import pexpect
import time 
import subprocess
import os, sys 
import glob
import re
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
from utils.agent_util import *
class Sandbox:
    def __init__(self, namespace, item, args):
        self.namespace = namespace
        self.client = docker.from_env()
        self.container = None
        self.shell = None
        self.args = args

    def get_project_path(self):
        project_path = self.container.exec_run("pwd").output.decode().strip()
        return project_path

    def start_container_build(self):
        image = f"{self.namespace}"
        self.container = self.client.containers.run(image, detach=True, tty=True, stdin_open=True, privileged=True)
        print(f"Container {self.container.short_id} started with image {image}")
        current_file_path = os.path.abspath(__file__)
        current_directory = os.path.dirname(current_file_path)
        project_directory = os.path.dirname(current_directory)
        
        cmd = f"chmod -R 777 {project_directory}/tools && docker cp {project_directory}/tools {self.container.name}:/home"
        subprocess.run(cmd, check=True, shell=True)

        cmd = f"chmod -R 777 {project_directory}/utils && docker cp {project_directory}/utils {self.container.name}:/home"
        subprocess.run(cmd, check=True, shell=True)

        cmd = f"docker cp {project_directory}/tools/fonts/opentype {self.container.name}:/usr/share/fonts"
        subprocess.run(cmd, check=True, shell=True)
        
    def start_container(self):
        image = f"{self.namespace}"
        host_path = '/tmp/patch'
        container_path = '/tmp/patch'
        self.container = self.client.containers.run(
            image, 
            detach=True, 
            tty=True, 
            stdin_open=True, 
            privileged=True,
            volumes={host_path: {'bind': container_path, 'mode': 'rw'},
            '/var/run/docker.sock': {'bind': '/var/run/docker.sock', 'mode': 'rw'}}
            )
        print(f"Container {self.container.name} {self.container.short_id} started with image {image}")
        
        current_file_path = os.path.abspath(__file__)
        current_directory = os.path.dirname(current_file_path)
        project_directory = os.path.dirname(current_directory)
        
        cmd = f"chmod -R 777 {project_directory}/tools && docker cp {project_directory}/tools {self.container.name}:/home"
        subprocess.run(cmd, check=True, shell=True)

        cmd = f"chmod -R 777 {project_directory}/utils && docker cp {project_directory}/utils {self.container.name}:/home"
        subprocess.run(cmd, check=True, shell=True)

        cmd = f"docker cp {project_directory}/tools/fonts/opentype {self.container.name}:/usr/share/fonts"
        subprocess.run(cmd, check=True, shell=True)

    def start_shell(self):
        if self.container:
            if self.shell and self.shell.isalive():
                self.shell.close(force=True) 
            command = f'docker exec -it {self.container.id} /bin/bash'
            self.shell = pexpect.spawn(command)
            self.shell.expect([r'\$ ', r'# '], timeout=30)  
        else:
            raise Exception("Container not started. Call start_container() first.")

    def get_session(self):
        self.start_shell()

        class Session:
            def __init__(self, sandbox):
                self.sandbox = sandbox

            def execute(self, command, timeout=180, type=True):
                try:
                    flag, output_info, command = command_check(command, self.sandbox.container.name)
                    if not flag:
                        return '### Observation: \n' + output_info
                    print('command:',command)
                    if command[-1] != '&':
                        self.sandbox.shell.sendline(command + "&& sleep 0.5")
                    else:
                        self.sandbox.shell.sendline(command)
                    self.sandbox.shell.expect([r'root@.*:.*# '], timeout=timeout)  

                    output = self.sandbox.shell.before.decode('utf-8',errors='ignore').strip()
                    output = output.replace('\x1b[?2004l\r', '')

                    output_lines = output.split('\r\n')
                    if len(output_lines) > 1:
                        output_lines = output_lines[1:-1]
                    result_message = '### Observation:' + '\n'.join(output_lines)

                    if not type:
                        max_length = 4000
                        truncation_length = 500
                        if len(result_message) > max_length:
                            result_message = result_message[:truncation_length] + "\n...\n[Output truncated for brevity]\n...\n" + result_message[-truncation_length:]
                    return result_message
                
                except pexpect.TIMEOUT:
                    partial_output = self.sandbox.shell.before.decode('utf-8').strip()
                    partial_output_lines = partial_output.split('\n')
                    if len(partial_output_lines) > 1:
                        partial_output_lines = partial_output_lines[1:-1]
                    partial_output = '\n'.join(partial_output_lines)
                    if not type:
                        max_length = 4000
                        truncation_length = 500
                        if len(partial_output) > max_length:
                            partial_output = partial_output[:truncation_length] + "\n...\n[Output truncated for brevity]\n...\n" + partial_output[-truncation_length:]
                    return '### Observation: ' + f"Error: Command '{command}' timed out after {timeout} seconds. Partial output:\n + {partial_output}"

            def edit(self, edit_tmp_file:str, project_path:str, file_path = None, start_line = 0, end_line = 0, timeout=60):
                if not file_path:
                    command = f"python3 /home/tools/code_edit.py -t '{edit_tmp_file}' -p '{project_path}'"
                else:
                    command = f"python3 /home/tools/code_edit.py -t '{edit_tmp_file}' -p '{project_path}' -f '{file_path}' -s {start_line} -e {end_line}"
                try:
                    self.sandbox.shell.sendline(command)
                    self.sandbox.shell.expect([r'root@.*:.*# '], timeout=timeout)

                    output = self.sandbox.shell.before.decode('utf-8').strip()
                    output_lines = output.split('\r\n')
                    if len(output_lines) > 1:
                        output_lines = output_lines[1:-1]  

                    result_message = '### Observation: ' + '\n'.join(output_lines)
                    return result_message

                except pexpect.TIMEOUT:
                    return '### Observation: ' + f"Error: Edit timed out after {timeout} seconds."
                
            def close(self):
                if self.sandbox.shell:
                    self.sandbox.shell.sendline('exit')
                    self.sandbox.shell.expect(pexpect.EOF, timeout=60)
                    self.sandbox.shell.close(force=True)
                    self.sandbox.shell = None  

        return Session(self)

    def stop_container(self):
        if self.container:
            if self.shell and self.shell.isalive():
                self.shell.close(force=True) 
                self.shell = None
            self.container.stop()
            self.container.remove()
            print(f"Container {self.container.short_id} stopped and removed")
            self.container = None


if __name__ == "__main__":
    sandbox = Sandbox("evaluate.agent.new", "", '')
    sandbox.start_container_build()
    session = sandbox.get_session()
