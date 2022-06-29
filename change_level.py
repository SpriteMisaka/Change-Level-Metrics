from pydriller import Repository
import pandas as pd
import sys
import math


def get_path(path):
    '''
        We use the root directory name as the subsystem name(i.e., to measure NS), the directory name
        to identify directories(i.e., ND) and the file name to identify files(i.e., NF).
    '''
    subsystem_path = path.split('\\')[0]
    dir_path = path[0:path.rfind('\\')] if '\\' in path else path
    return subsystem_path, dir_path


if __name__ == '__main__':

    index = 0

    df = pd.DataFrame(columns=sorted(["NAME", "NS", "ND", "NF", "ENTROPY", "LA", "LD", "LT", "FIX",
        "NDEV", "AGE", "NUC", "EXP", "REXP", "SEXP"]))

    repo = sys.argv[1]

    # ===== History ======================
    authors_of = {}
    last_commit_of = {}
    commit_times_of = {}
    
    past_modified_file_names = []


    # ===== Experience ===================
    exp_date_of = {}
    subsystem_exp_of = {}


    for commit in Repository(repo).traverse_commits():

        change_matters = False
        
        author = commit.author.name
        author_date = commit.author_date

        # ===== Diffusion ====================
        modified_lines = []
        
        subsystem_path_set = set()
        dir_path_set = set()
        path_set = set()


        # ===== Size =========================
        added_lines_sum = 0
        deleted_lines_sum = 0
        loc_before_sum = 0
        
        
        # ===== History ======================
        interval_of = {}
        
        
        for mod in commit.modified_files:
        
            if mod.filename.endswith(('.cpp', '.c', '.h', '.cc', '.java', '.py', '.cs')):
            
                change_matters = True
                type = mod.change_type.name
                
                # ===== Diffusion ====================
                lines = mod.added_lines + mod.deleted_lines
                if lines > 0:
                    modified_lines.append(lines)
                
                path = mod.old_path if type == 'DELETE' else mod.new_path
                subsystem_path, dir_path = get_path(path)

                subsystem_path_set.add(subsystem_path)
                dir_path_set.add(dir_path)
                path_set.add(path)
                
                
                # ===== Size =========================
                added_lines_sum += mod.added_lines
                deleted_lines_sum += mod.deleted_lines

                if type == 'MODIFY' or type == 'DELETE':
                    loc_before_sum += mod.source_code_before.count('\n') + 1
                
                
                # ===== History ======================
                if mod.filename not in authors_of:
                    authors_of[mod.filename] = set()
                authors_of[mod.filename].add(author)

                if mod.filename in last_commit_of:
                    interval_of[mod.filename] = (author_date - last_commit_of[mod.filename]).days
                last_commit_of[mod.filename] = author_date


        if change_matters:
        
            m = {}
        
            # ===== Diffusion ====================
            '''
                NS: Number of modified subsystems
            '''
            m["NS"] = len(subsystem_path_set)
            
            '''
                ND: Number of modified directories
            '''
            m["ND"] = len(dir_path_set)
            
            '''
                NF: Number of modified files
            '''
            m["NF"] = len(path_set)

            '''
                ENTROPY: Distribution of modified code across each file
            '''
            modified_lines_sum = 0
            entropy = 0.0
            for i in modified_lines:
                modified_lines_sum += i
            if modified_lines_sum != 0:
                '''
                    Entropy is defined as: $H(P) = -\sum^{n}_{k=1}(p_k * \log_2 p_k)$.
                    
                    If, for example, a change modifies three different files, A, B, and C and the
                    number of modified lines in files A, B, and C is 30, 20, and 10 lines, respectively,
                    then the Entropy is measured as 1.46.
                '''
                for i in modified_lines:
                    tmp = i / modified_lines_sum
                    entropy -= tmp * math.log(tmp, 2)
            m["ENTROPY"] = entropy
            
            
            # ===== Size =========================
            '''
                LA: Lines of code added
            '''
            m["LA"] = added_lines_sum
            
            '''
                LD: Lines of code deleted
            '''
            m["LD"] = deleted_lines_sum
            
            '''
                LT: Lines of code in a file before the change
            '''
            m["LT"] = loc_before_sum
            
            
            # ===== Purpose ======================
            '''
                FIX: Whether or not the change is a defect fix
                
                To determine whether or not a change fixes a defect, we search the change logs for
                keywords like "bug", "fix", "defect" or "patch" and for defect identification numbers.
            '''
            purpose_keywords = ['bug', 'Bug', 'bugs', 'Bugs', 'fix', 'fixed', 'fixing',
                'Fix', 'Fixed', 'Fixing', 'defect', 'Defect', 'patch', 'Patch']
            purpose = any(map(lambda w: w in commit.msg, purpose_keywords))
            m["FIX"] = purpose
            
            
            # ===== History ======================
            modified_file_names = [i.filename for i in commit.modified_files]
            past_modified_file_names.append(modified_file_names)
            
            '''
                NDEV: The number of developers that changed the modified files
                
                For example, if a change has files A, B, and C, file A thus far has been modified
                by developer x, and files B and C have been modified by developers x and y, then
                NDEV would be 2(x and y).
            '''
            authors_of_files = set()
            for k, v in authors_of.items():
                if k in modified_file_names:
                    for i in v:
                        authors_of_files.add(i)
            m["NDEV"] = len(authors_of_files)
            
            '''
                AGE: The average time interval between the last and the current change
                
                For example, if file A was last modified three days ago, file B was modified five
                days ago, and file C was modified four days ago, then AGE is calculated as 4.
            '''
            interval_sum = 0
            for _, v in interval_of.items():
                interval_sum += v
            m["AGE"] = interval_sum / len(interval_of.items()) if len(interval_of.items()) > 0 else 0
            
            '''
                NUC: The number of unique changes to the modified files
                
                For example, if file A was previously modified in change x and files B and C were
                modified in change y, then NUC is 2(x and y).
            '''
            changes_of_files = 0
            for i in past_modified_file_names:
                if set(modified_file_names).issubset(i):
                    changes_of_files += 1
            m["NUC"] = changes_of_files
            
            
            # ===== Experience ===================
            '''
                REXP: Recent developer experience
                
                Recent experience(REXP) is measured as the total experience of the developer in terms
                of changes, weighted by their age.
                
                For example, if a developer of a change made three changes in the current year, four
                changes one year ago, and three changes two years ago, then REXP is 6.
                (i.e., $\frac{3}{1} + \frac{4}{2} + \frac{3}{3}$)
            '''
            r_exp = 0
            if author not in exp_date_of:
                exp_date_of[author] = []
            exp_date_of[author].append(author_date)
            for k, v in exp_date_of.items():
                if k == author:
                    '''
                        We use the following weighting scheme to measure REXP: $\frac{1}{n+1}$, where
                        $n$ is measured in years.
                    '''
                    t = [((author_date - i).days // 365) + 1 for i in v]
                    for i in t:
                        if i != 0: r_exp += 1 / i
                    break
            m["REXP"] = r_exp

            '''
                SEXP: Developer experience on a subsystem
                
                Subsystem experience(SEXP) measures the number of changes the developer made in the past
                to the subsystems that are modified by the current change.
            '''
            s_exp = 0
            if author not in subsystem_exp_of:
                subsystem_exp_of[author] = {}
            for i in subsystem_path_set:
                if i not in subsystem_exp_of[author]:
                    subsystem_exp_of[author][i] = 0
                subsystem_exp_of[author][i] += 1
                
                s_exp += subsystem_exp_of[author][i]
            m["SEXP"] = s_exp
            
            '''
                EXP: Developer experience
                
                Developer experience(EXP) is measured as the number of changes made by the developer
                before the current change.
            '''
            exp = 0
            for k, v in subsystem_exp_of.items():
                if k == author:
                    for _, j in v.items():
                        exp += j
            m["EXP"] = exp
            
            
            m["NAME"] = commit.hash
            m = sorted(m.items(), key=lambda x: x[0])
            v = [i[0] for i in m]
            
            for (key, value) in m:
                if key in v:
                    df.loc[index, key] = value
            
            index += 1

    df.to_csv("data.csv", index=False)
