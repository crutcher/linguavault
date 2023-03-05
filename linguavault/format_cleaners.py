import json

import json5


def paranoid_json(source: str) -> str:
    raw = source[source.find("{") : source.rfind("}") + 1]
    return json.dumps(json5.loads(raw))


def reblock(text: str) -> str:
    lines: list[str] = []

    in_block = False
    for line in text.strip().splitlines():
        line = line.strip()
        previous_line = lines[-1] if lines else None

        if not previous_line:
            lines.append(line)
            continue

        else:
            lines[-1] = f"{previous_line} {line}"
            continue

    return "\n".join(lines)
