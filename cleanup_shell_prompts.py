import re

# يلتقط بدايات سطور بايثون التفاعلية (>>> ...) أو النقاط الثلاث (...)
SHELL_PROMPT_PATTERN = re.compile(r'^\s*(>>>|\.\.\.)\s?')


def cleanup_shell_prompts(path: str) -> None:
    """
    يزيل علامات الموجه التفاعلي (>>> أو ...) من كل سطر في الملف.
    """
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    cleaned_lines = [SHELL_PROMPT_PATTERN.sub('', line) for line in lines]

    with open(path, 'w', encoding='utf-8') as f:
        f.writelines(cleaned_lines)
