# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Xinchen Wang 王欣辰

import argparse
import json
import multiprocessing
import os
import sys
from datetime import datetime
from agents.construct import Constructor
from agents.comprehend import Comprehender
from agents.plan_analyze import PlanAnalyzer
from agents.score_report import ScoreReporter
from utils.sandbox import Sandbox
from utils.agent_util import *
import subprocess
import traceback

def run_evaluation(args, item, index, model):

    output_path = os.path.join(args.write_path, model, 'output')
    output_file_path = os.path.join(output_path, f'{item["id"]}.log')
    report_path = os.path.join(args.write_path, model, 'report')
    log_path = os.path.join(args.write_path, model, 'log')
    data_path = os.path.join(args.write_path, model, 'data')

    if not os.path.exists(log_path):
        os.makedirs(log_path)
    if not os.path.exists(report_path):
        os.makedirs(report_path)
    if not os.path.exists(output_path):
        os.makedirs(output_path)
    if not os.path.exists(data_path):
        os.makedirs(data_path)

    with open(output_file_path, 'w') as log_file:
        sys.stdout = log_file
        try:
            now = datetime.now()
            datetime_str = now.strftime('%Y%m%d%H%M%S')
            print("time: ", datetime_str)
            trajectory = []
            namespace = "codevisionary.evaluate"
            sandbox = Sandbox(namespace, item, args)
            sandbox.start_container() # 启动沙箱
            project_path = sandbox.get_project_path()
            container_name = sandbox.container.name
            
            comprehender = Comprehender(sandbox)
            trajectory, comprehend_report = comprehender.run(project_path,item, trajectory, args)     
            with open(f'{data_path}/comprehend_report.jsonl', 'a') as wf:
                data = {'id': item["id"], 'conprehend_report': comprehend_report}
                json.dump(data, wf, ensure_ascii=False)
                wf.write('\n')

            constructor = Constructor(sandbox)
            trajectory, build_report = constructor.run(project_path,item, trajectory, comprehend_report, args)
            with open(f'{data_path}/build_report.jsonl', 'a') as wf:
                data = {'id': item["id"], 'build_report': build_report}
                json.dump(data, wf, ensure_ascii=False)
                wf.write('\n')

            plananalyzer = PlanAnalyzer(sandbox)
            trajectory, specialized_report, single_step_reports, images_path = plananalyzer.run(project_path,item, trajectory, build_report, comprehend_report, args)
            with open(f'{data_path}/single_step_report.jsonl', 'a') as wf:
                data = {'id': item["id"], 'single_step_report': specialized_report, 'single_step_reports': single_step_reports}
                json.dump(data, wf, ensure_ascii=False)
                wf.write('\n')

            scorereporter = ScoreReporter(sandbox, args)
            trajectory, final_score, overall_report, inter_scores_list, inter_scores_per_list = scorereporter.run(project_path,item, trajectory, build_report, comprehend_report, specialized_report, args)
            with open(f'{data_path}/evaluation_score.jsonl', 'a') as wf:
                data = {'id': item["id"], 'evaluation_score': final_score, 'overall_report': overall_report}
                json.dump(data, wf, ensure_ascii=False)
                wf.write('\n')
            
            final_report = generate_report(item = item, final_score = final_score, comprehend_report=comprehend_report, build_report = build_report, specialized_report = specialized_report, overall_report = overall_report)
            write_path = save_report(id = item["id"], container_name = container_name, report_path=report_path, report=final_report, images_path=images_path)
            save_trajectory(id = item["id"], traj_dir = log_path, trajectory=trajectory)

            if args.lint:
                execute_markdown_lint(write_path)

            if args.pdf:
                execute_generate_pdf(write_path)

            sandbox.stop_container()
            now = datetime.now()
            datetime_str = now.strftime('%Y%m%d%H%M%S')
            print("time: ", datetime_str)
            print(f"This instance has been successfully resolved!!")
        except Exception as e:
            print(f"Error occurred: {e}")
            traceback.print_exc()  # 打印完整的错误堆栈信息
            sandbox.stop_container()
        finally:
            sys.stdout = sys.__stdout__

def worker(task_queue):
    while True:
        task = task_queue.get()
        if task is None:
            break
        args, item, index, model = task
        run_evaluation(args, item, index, model)

def main(args):
    num_processes = 5 
    num_tasks = -1

    task_queue = multiprocessing.Queue()
    
    pool = []
    for _ in range(num_processes):
        p = multiprocessing.Process(target=worker, args=(task_queue,))
        p.start()
        pool.append(p)
    
    jsonList = []
    with open(args.evaluation_path, 'r') as file:
        rawdata = file.readlines()
        for line in rawdata:
            jsonList.append(json.loads(line))

    tasks = []
    for i, jL in enumerate(jsonList):
        data = {'id': jL['id'], 'query': jL['question'], 'answer': jL[f'response'], 'model': jL['model']}
        tasks.append((args, data, i+1, data['model']))

    print(len(tasks))

    for task in tasks:
        task_queue.put(task)
    
    for _ in range(num_processes):
        task_queue.put(None)

    for p in pool:
        p.join()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Script to handle paths.")
    parser.add_argument("--evaluation_path", required=True, help="Path to the input file to be evaluated")
    parser.add_argument("--write_path", required=True, help="Directory where the output files will be saved")
    parser.add_argument("--pdf", action="store_true", help="Generate the pdf")
    parser.add_argument("--lint", action="store_true", help="Check the markdown")
    args = parser.parse_args()
    main(args)