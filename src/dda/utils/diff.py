import difflib


def pretty_diff(string1, string2) -> str:
    lines1 = string1.splitlines()
    lines2 = string2.splitlines()

    diff = difflib.unified_diff(lines1, lines2, lineterm="")

    result = []
    for line in diff:
        if line.startswith("-"):
            result.append(f"\033[31m{line}\033[0m")  # Red for removals
        elif line.startswith("+"):
            result.append(f"\033[32m{line}\033[0m")  # Green for additions
        else:
            result.append(line)
    return '\n'.join(result)
