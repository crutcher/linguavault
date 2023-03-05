import os

import openai

OPENAI_SECRETS_SEARCH_PATHS: list[str] = [
    "~/.openai_keys",
]


def load_openai_secrets(secrets_file: str = None) -> None:
    """Load secrets into openai client."""
    if secrets_file is None:
        for path in OPENAI_SECRETS_SEARCH_PATHS:
            path = os.path.expanduser(path)
            if os.path.exists(path):
                secrets_file = path

    path = os.path.expanduser(secrets_file)

    with open(path) as f:
        secrets = dict(
            sline.split("=")
            for line in f.readlines()
            for sline in [line.strip()]
            if sline
        )

    openai.organization = secrets["OPENAI_ORGANIZATION"]
    openai.api_key = secrets["OPENAI_API_KEY"]


def completion(prefix: str, query: str) -> str:
    result = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            dict(role="system", content=prefix),
            dict(role="user", content=query),
        ],
    )
    return result["choices"][0]["message"]["content"]
