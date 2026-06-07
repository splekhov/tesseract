#!/usr/bin/env python3

import subprocess
from collections import defaultdict

def get_processes():
    # Get PID, PPID, and command
    result = subprocess.run(
        ["ps", "-axo", "pid,ppid,comm"],
        capture_output=True,
        text=True,
        check=True
    )
    lines = result.stdout.strip().split("\n")[1:]
    
    processes = {}
    children = defaultdict(list)

    for line in lines:
        parts = line.strip().split(None, 2)
        pid = int(parts[0])
        ppid = int(parts[1])
        cmd = parts[2] if len(parts) > 2 else ""

        processes[pid] = cmd
        children[ppid].append(pid)

    return processes, children


def print_tree(pid, processes, children, prefix=""):
    name = processes.get(pid, "unknown")
    print(f"{prefix}{pid} {name}")

    child_list = sorted(children.get(pid, []))
    for i, child in enumerate(child_list):
        is_last = i == len(child_list) - 1
        branch = "└─ " if is_last else "├─ "
        extension = "   " if is_last else "│  "
        print_tree(child, processes, children, prefix + branch)


def main():
    processes, children = get_processes()

    # root processes (ppid = 0 or 1 depending on macOS version)
    roots = sorted(children.get(0, []) + children.get(1, []))

    seen = set()
    for root in roots:
        if root not in seen:
            print_tree(root, processes, children)
            seen.add(root)


if __name__ == "__main__":
    main()

