# part of the code edit tool is from: https://github.com/Aider-AI/aider/blob/cecfbc7e207eba1961f2cfad32ff544242e3e9aa/aider/coders/editblock_coder.py

import math
import re
from difflib import SequenceMatcher
import difflib
from pathlib import Path
import tempfile
import os
import subprocess
import argparse

DIFF_FENCE = ["```diff", "```"]
HEAD = "<<<<<<< SEARCH"
DIVIDER = "======="
UPDATED = ">>>>>>> REPLACE"
MASK = "!MASK_CHAR_MASK_CHAR_MASK_CHAR!!MASK_CHAR_MASK_CHAR_MASK_CHAR!!MASK_CHAR_MASK_CHAR_MASK_CHAR!"
separators = "|".join([HEAD, DIVIDER, UPDATED])
split_re = re.compile(r"^((?:" + separators + r")[ ]*\n)", re.MULTILINE | re.DOTALL)
USE_LINT_CHECKER = False

def contains_line_number(string):
    rev_lineno_regex = r'^【\d+】\s*'
    matches = re.findall(rev_lineno_regex, string, re.MULTILINE)
    return bool(matches)

def check_label_number(text): 
    count_head = text.count(HEAD)
    count_divider = text.count(DIVIDER)
    count_updated = text.count(UPDATED)
    markers_equal = count_head == count_divider == count_updated
    return markers_equal

def generate_diff(old_code, new_code, filename):
    if old_code == new_code:
        return ""
    stripped_old_code = old_code.strip()
    stripped_new_code = new_code.strip()

    diff = difflib.unified_diff(
        stripped_old_code.splitlines(keepends=True),
        stripped_new_code.splitlines(keepends=True),
        fromfile=filename,
        tofile=filename
    )

    diff_text = "".join(diff)
    return diff_text

def strip_filename(filename, fence):
    filename = filename.strip()

    if filename == "...":
        return

    start_fence = fence[0]
    if filename.startswith(start_fence):
        return

    filename = filename.rstrip(":")
    filename = filename.lstrip("#")
    filename = filename.strip()
    filename = filename.strip("`")
    filename = filename.strip("*")
    filename = filename.replace("\\_", "_")
    return filename

def diff_files(file1, file2, file_path):
    a = file1.splitlines()
    b = file2.splitlines()
    diff = difflib.unified_diff(
        a,
        b,
        fromfile='a/' + file_path,
        tofile='b/' + file_path,
        lineterm=''
    )
    return "\n".join(diff)

def write_text(filename, content):
    with open(str(filename), "w", encoding='utf-8') as f:
        f.write(content)

def apply_edit(filePath, fileContent, search, replace):
    new_content = do_replace(filePath, fileContent, search, replace, DIFF_FENCE)
    if new_content:
        fileContent = fileContent.replace(MASK, '')
        new_content = new_content.replace(MASK, '')
    if not new_content:
        res = f"#SEARCH/REPLACE block failed to match!\n"
        res += f"""
## SearchReplaceNoExactMatch: This SEARCH block failed to exactly match lines in {filePath}
{search}

"""
        did_you_mean = find_similar_lines(search, fileContent)
        if did_you_mean:
            res += f"""Did you mean to match some of these actual lines from {filePath}?

{DIFF_FENCE[0]}
{did_you_mean}
{DIFF_FENCE[1]}

"""

        if replace in fileContent:
                res += f"""Are you sure you need this SEARCH/REPLACE block?
The REPLACE lines are already in {filePath}!

"""
        res += "The SEARCH section must exactly match an existing block of lines including all white space, comments, indentation, docstrings, etc\n"
        res = res.replace(MASK, '')
        return {'message': res,'diff': ''}

    diff = diff_files(fileContent, new_content, filePath)

    if USE_LINT_CHECKER:
        original_file_name = os.path.basename(filePath)
        with tempfile.NamedTemporaryFile(mode='w', delete=True, prefix=original_file_name) as temp:
            fileContent = fileContent.replace(MASK, '')
            temp.write(fileContent)
            temp.flush() 
            temp_name = temp.name
            command_options = f"pylint {temp_name} --disable=all --enable=E0001"
            result = subprocess.run(command_options, shell=True, capture_output=True, text=True)
            if ('E0001' in result.stdout) or ('E0001' in result.stderr):
                if len(diff) != 0:
                    diff = diff.replace(MASK, '')
                    write_text(filePath, new_content) 
                    return {'message': 'succeed','diff': diff + '\n\n'}
                else:
                    return {'message': 'Fail to apply diff(s)','diff': ''}

        with tempfile.NamedTemporaryFile(mode='w', delete=True, prefix=original_file_name) as temp:
            new_content = new_content.replace(MASK, '')
            temp.write(new_content)
            temp.flush() 
            temp_name = temp.name
            command_options = f"pylint {temp_name} --disable=all --enable=E0001"
            result = subprocess.run(command_options, shell=True, capture_output=True,text=True)
            if ('E0001' in result.stdout) or ('E0001' in result.stderr):
                if len(diff) != 0:
                    diff = diff.replace(MASK, '')
                return {'message': result.stdout + result.stderr, 'diff': diff + '\n\n'}

    if len(diff) != 0:
        write_text(filePath, new_content) 
        diff = diff.replace(MASK, '')
        return {'message': 'succeed','diff': diff + '\n\n'}
    else:
        return {'message': 'Fail to apply diff(s)','diff': ''}


def prep(content):
    if content and not content.endswith("\n"):
        content += "\n"
    lines = content.splitlines(keepends=True)
    return content, lines


def perfect_or_whitespace(whole_lines, part_lines, replace_lines):
    res = perfect_replace(whole_lines, part_lines, replace_lines)
    if res:
        return res

    res = replace_part_with_missing_leading_whitespace(whole_lines, part_lines, replace_lines)
    if res:
        return res


def perfect_replace(whole_lines, part_lines, replace_lines):
    part_tup = tuple(part_lines)
    part_len = len(part_lines)

    for i in range(len(whole_lines) - part_len + 1):
        whole_tup = tuple(whole_lines[i : i + part_len])
        if part_tup == whole_tup:
            res = whole_lines[:i] + replace_lines + whole_lines[i + part_len :]
            return "".join(res)


def replace_most_similar_chunk(whole, part, replace):
    """Best efforts to find the `part` lines in `whole` and replace them with `replace`"""

    whole, whole_lines = prep(whole)
    part, part_lines = prep(part)
    replace, replace_lines = prep(replace)

    res = perfect_or_whitespace(whole_lines, part_lines, replace_lines)
    if res:
        return res

    if len(part_lines) > 2 and not part_lines[0].strip():
        skip_blank_line_part_lines = part_lines[1:]
        res = perfect_or_whitespace(whole_lines, skip_blank_line_part_lines, replace_lines)
        if res:
            return res

    try:
        res = try_dotdotdots(whole, part, replace)
        if res:
            return res
    except ValueError:
        pass

    return


def try_dotdotdots(whole, part, replace):
    """
    See if the edit block has ... lines.
    If not, return none.

    If yes, try and do a perfect edit with the ... chunks.
    If there's a mismatch or otherwise imperfect edit, raise ValueError.

    If perfect edit succeeds, return the updated whole.
    """

    dots_re = re.compile(r"(^\s*\.\.\.\n)", re.MULTILINE | re.DOTALL)

    part_pieces = re.split(dots_re, part)
    replace_pieces = re.split(dots_re, replace)

    if len(part_pieces) != len(replace_pieces):
        raise ValueError("Unpaired ... in SEARCH/REPLACE block")

    if len(part_pieces) == 1:
        return

    all_dots_match = all(part_pieces[i] == replace_pieces[i] for i in range(1, len(part_pieces), 2))

    if not all_dots_match:
        raise ValueError("Unmatched ... in SEARCH/REPLACE block")

    part_pieces = [part_pieces[i] for i in range(0, len(part_pieces), 2)]
    replace_pieces = [replace_pieces[i] for i in range(0, len(replace_pieces), 2)]

    pairs = zip(part_pieces, replace_pieces)
    for part, replace in pairs:
        if not part and not replace:
            continue

        if not part and replace:
            if not whole.endswith("\n"):
                whole += "\n"
            whole += replace
            continue

        if whole.count(part) == 0:
            raise ValueError
        if whole.count(part) > 1:
            raise ValueError

        whole = whole.replace(part, replace, 1)

    return whole


def replace_part_with_missing_leading_whitespace(whole_lines, part_lines, replace_lines):
    leading = [len(p) - len(p.lstrip()) for p in part_lines if p.strip()] + [
        len(p) - len(p.lstrip()) for p in replace_lines if p.strip()
    ]

    if leading and min(leading):
        num_leading = min(leading)
        part_lines = [p[num_leading:] if p.strip() else p for p in part_lines]
        replace_lines = [p[num_leading:] if p.strip() else p for p in replace_lines]

 
    num_part_lines = len(part_lines)

    for i in range(len(whole_lines) - num_part_lines + 1):
        add_leading = match_but_for_leading_whitespace(
            whole_lines[i : i + num_part_lines], part_lines
        )

        if add_leading is None:
            continue

        replace_lines = [add_leading + rline if rline.strip() else rline for rline in replace_lines]
        whole_lines = whole_lines[:i] + replace_lines + whole_lines[i + num_part_lines :]
        return "".join(whole_lines)

    return None


def match_but_for_leading_whitespace(whole_lines, part_lines):
    num = len(whole_lines)

    if not all(whole_lines[i].lstrip() == part_lines[i].lstrip() for i in range(num)):
        return

    add = set(
        whole_lines[i][: len(whole_lines[i]) - len(part_lines[i])]
        for i in range(num)
        if whole_lines[i].strip()
    )

    if len(add) != 1:
        return

    return add.pop()


def replace_closest_edit_distance(whole_lines, part, part_lines, replace_lines):
    similarity_thresh = 0.8

    max_similarity = 0
    most_similar_chunk_start = -1
    most_similar_chunk_end = -1

    scale = 0.1
    min_len = math.floor(len(part_lines) * (1 - scale))
    max_len = math.ceil(len(part_lines) * (1 + scale))

    for length in range(min_len, max_len):
        for i in range(len(whole_lines) - length + 1):
            chunk = whole_lines[i : i + length]
            chunk = "".join(chunk)

            similarity = SequenceMatcher(None, chunk, part).ratio()

            if similarity > max_similarity and similarity:
                max_similarity = similarity
                most_similar_chunk_start = i
                most_similar_chunk_end = i + length

    if max_similarity < similarity_thresh:
        return

    modified_whole = (
        whole_lines[:most_similar_chunk_start]
        + replace_lines
        + whole_lines[most_similar_chunk_end:]
    )
    modified_whole = "".join(modified_whole)

    return modified_whole

def strip_quoted_wrapping(res, fname=None, fence=DIFF_FENCE):
    """
    Given an input string which may have extra "wrapping" around it, remove the wrapping.
    For example:

    filename.ext
    ```
    We just want this content
    Not the filename and triple quotes
    ```
    """
    if not res:
        return res

    res = res.splitlines()

    if fname and res[0].strip().endswith(Path(fname).name):
        res = res[1:]

    if res[0].startswith(fence[0]) and res[-1].startswith(fence[1]):
        res = res[1:-1]

    res = "\n".join(res)
    if res and res[-1] != "\n":
        res += "\n"

    return res


def do_replace(fname, content, before_text, after_text, fence=None):
    before_text = strip_quoted_wrapping(before_text, fname, fence)
    after_text = strip_quoted_wrapping(after_text, fname, fence)

    if content is None:
        return

    new_content = replace_most_similar_chunk(content, before_text, after_text)

    return new_content

missing_filename_err = (
    "Bad/missing filename. The filename must be alone on the line before the opening fence"
    " {fence[0]}"
)

def find_similar_lines(search_lines, content_lines, threshold=0.6):
    search_lines = search_lines.splitlines()
    content_lines = content_lines.splitlines()

    best_ratio = 0
    best_match = None

    for i in range(len(content_lines) - len(search_lines) + 1):
        chunk = content_lines[i : i + len(search_lines)]
        ratio = SequenceMatcher(None, search_lines, chunk).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_match = chunk
            best_match_i = i

    if best_ratio < threshold:
        return ""

    if best_match[0] == search_lines[0] and best_match[-1] == search_lines[-1]:
        return "\n".join(best_match)

    N = 5
    best_match_end = min(len(content_lines), best_match_i + len(search_lines) + N)
    best_match_i = max(0, best_match_i - N)

    best = content_lines[best_match_i:best_match_end]
    return "\n".join(best)

def parse_diffs_block(content, fence=DIFF_FENCE):
    if not content.endswith("\n"):
        content = content + "\n"

    pieces = re.split(split_re, content)

    pieces.reverse()
    processed = []
    results = []  

    current_filename = None
    try:
        while pieces:
            cur = pieces.pop()

            if cur in (DIVIDER, UPDATED):
                processed.append(cur)
                raise ValueError(f"Unexpected {cur}")

            if cur.strip() != HEAD:
                processed.append(cur)
                continue

            processed.append(cur)  
            
            filename = strip_filename(processed[-2].splitlines()[-1], fence)
            try:
                if not filename:
                    filename = strip_filename(processed[-2].splitlines()[-2], fence)
                if not filename:
                    if current_filename:
                        filename = current_filename
                    else:
                        raise ValueError(missing_filename_err.format(fence=fence))
            except IndexError:
                if current_filename:
                    filename = current_filename
                else:
                    raise ValueError(missing_filename_err.format(fence=fence))

            current_filename = filename

            original_text = pieces.pop()
            processed.append(original_text)

            divider_marker = pieces.pop()
            processed.append(divider_marker)
            if divider_marker.strip() != DIVIDER:
                raise ValueError(f"Expected `{DIVIDER}` not {divider_marker.strip()}")

            updated_text = pieces.pop()
            processed.append(updated_text)

            updated_marker = pieces.pop()
            processed.append(updated_marker)
            if updated_marker.strip() != UPDATED:
                raise ValueError(f"Expected `{UPDATED}` not `{updated_marker.strip()}")

            results.append((filename, original_text, updated_text))
    except ValueError as e:
        processed = "".join(processed)
        err = e.args[0]
        raise ValueError(f"{processed}\n^^^ {err}")
    except IndexError:
        processed = "".join(processed)
        raise ValueError(f"{processed}\n^^^ Incomplete SEARCH/REPLACE block.")
    except Exception:
        processed = "".join(processed)
        raise ValueError(f"{processed}\n^^^ Error parsing SEARCH/REPLACE block.")
    return results

def insert_char_outside_range(text, edit_range, mask = MASK):

    lines = text.splitlines(True)
    extend = 3
    for i in range(len(lines)):
        if i < (edit_range["start_line"] - extend - 1):
            lines[i] = mask + lines[i]
        if i > (edit_range["end_line"] + extend - 1):
            lines[i] = mask + lines[i]

    return ''.join(lines)


def process_diff(text:str, project_path: str, edit_range = None):
    succeed_patches = ''
    fail_patches = ''
    edits = ''
    if contains_line_number(text): 
        fail_patches = "* Fail Patch: ERROR! Do not contain the line number in patch! Please remove the line numbers and keep the indentation correct."
        return fail_patches
    if not check_label_number(text):
        fail_patches =  f"""* Fail Patch: ERROR! Your change request contains incomplete patche(es).  Provide patches in following format:
###Thought: modify ...
###Action:                
{DIFF_FENCE[0]}
/absolute/path/of/modified_file.py
{HEAD}
    exact copy of old line(s) you would like to change, 2~20 lines recommend!
{DIVIDER}
    new line(s) to replace
{UPDATED}

{HEAD}
    exact copy of old line(s) you would like to change, 2~20 lines recommend!
{DIVIDER}
    new line(s) to replace
{UPDATED}
{DIFF_FENCE[1]}
"""
        return fail_patches
    try:
        edits = parse_diffs_block(text)
    except Exception as e:
        err = str(e)
        fail_patches += err

    if len(edits) == 0:
        fail_patches =  f"""* Fail Patch: ERROR! No patch found that meets the format requirements. Provide patches in following format:
###Thought: modify ...
###Action:                
{DIFF_FENCE[0]}
/absolute/path/of/modified_file.py
{HEAD}
    exact copy of old line(s) you would like to change
{DIVIDER}
    new line(s) to replace
{UPDATED}
{DIFF_FENCE[1]}
"""
        return fail_patches

    for filename, original_text, updated_text in edits:
        if len(original_text.strip()) == 0:
            if edit_range:
                print("Error! Old lines can not be empty in edit limit mode!")
                continue
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as file:
                    original_content = file.read()
                new_content = updated_text + original_content
                diff_message = generate_diff(original_content, new_content, filename.replace(project_path,''))
                succeed_patches += f"The new code snippet is inserted at the beginning of the file {filename}\n" + diff_message
                with open(filename, 'w', encoding='utf-8') as file:
                    file.write(new_content)
            else: 
                try:
                    with open(filename, 'w') as f:
                        f.write(updated_text)
                    succeed_patches += f"Create and write {filename}!\n"
                except Exception as err:
                    fail_patches += f"ERROR! Create and write {filename} failed!\n{err}\n"
                continue
        else:
            if edit_range:
                if filename.strip() != edit_range["file_path"].strip():
                    print("Error! You can only edit the code you are responsible for!")
                    continue
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as file:
                    original_content = file.read()

                diff_msgs = apply_edit(filename, original_content, original_text, updated_text)
                if not diff_msgs['diff'].strip(): 
                    fail_patches += diff_msgs['message']
                    if edit_range:
                        fail_patches += "\nMake sure your changes' old line(s) are within the [User Given Code] range!"
                elif diff_msgs['message'] == 'succeed': 
                    patch_string = diff_msgs['diff'].replace(project_path, '')
                    patch_string = patch_string.replace('//', '/')
                    succeed_patches += patch_string
                else: 
                    fail_patches += (f"ERROR! The patch does not pass the lint check and fail to apply. Try to fix the lint error:\n"
                                     f"### lint message:\n{diff_msgs['message']}\n")
            else: 
                fail_patches += f"ERROR! The file {filename} does not exist.\n"
    
    patch_apply_result = f"* Succeed Patch:\n{succeed_patches}"
    if len(fail_patches) != 0:
        patch_apply_result += f"* Fail Patch:\n{fail_patches}"
        if not edit_range:
            patch_apply_result += """
TIPS:
* All patches must be based on the original code. Make sure it and try to provide more sufficient and unique old line(s) from snippet to facilitate matching.
* Make sure your patch has right indentation.
* Make sure your file path is correct."""
    return patch_apply_result



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Search Class in repo.')
    parser.add_argument('-t', '--patch_tmp_file', help='patch file', required=True)
    parser.add_argument('-p', '--project_path', help='path of repo', required=True)
    parser.add_argument('-f', '--file_path', help='file path', required=False)
    parser.add_argument('-s', '--start_line', type=int, help='start line', required=False)
    parser.add_argument('-e', '--end_line', type=int, help='end line', required=False)
    args = parser.parse_args()

    with open(args.patch_tmp_file, 'r') as file:
        content = file.read()
    edit_range = {}

    if args.file_path:
        edit_range["file_path"] = args.file_path
        edit_range["start_line"] = args.start_line
        edit_range["end_line"] = args.end_line
        
        with open(edit_range["file_path"], 'r', encoding='utf-8') as file:
            target_original_content = file.read()

        target_masked_content = insert_char_outside_range(target_original_content, edit_range)
        with open(edit_range["file_path"], 'w', encoding='utf-8') as file:
            file.write(target_masked_content)
            
    print(process_diff(content, args.project_path, edit_range))

    if args.file_path:
        target_masked_content = ''
        with open(edit_range["file_path"], 'r', encoding='utf-8') as file:
            target_masked_content = file.read()
        target_unmasked_content = target_masked_content.replace(MASK, '')
        with open(edit_range["file_path"], 'w', encoding='utf-8') as file:
            file.write(target_unmasked_content)