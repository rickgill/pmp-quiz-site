from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from pypdf import PdfReader


LEGACY_QUESTION_START_RE = re.compile(r"Topic\s+\d+Question\s+#(\d+)", re.IGNORECASE)
INLINE_OPTION_RE = re.compile(r"(?:^|\n)([A-E])\.\s*(.+?)(?=(?:\n[A-E]\.\s)|(?:\nAnswer\s*:)|\Z)", re.DOTALL)
INLINE_ANSWER_RE = re.compile(r"Answer\s*:\s*([A-E])", re.IGNORECASE)
PMSTUDY_OPTION_RE = re.compile(
    r"\(\s*([a-d])\s*\)\s*(.+?)(?=(?:\n\s*\(\s*[a-d]\s*\))|(?:\n\s*Go to the Answer)|\Z)",
    re.IGNORECASE | re.DOTALL,
)
PMSTUDY_ANSWER_RE = re.compile(r"Answer-(\d+):\s*([a-d])\b", re.IGNORECASE)


def normalize_text(value: str) -> str:
    replacements = {
        "\x00": "fi",
        "\u00a0": " ",
        "\u200b": "",
        "\uf013": " ",
        "\uf017": " ",
        "\uf007": " ",
        "\uf147": " ",
        "\uf164": " ",
        "\t": " ",
    }
    for old, new in replacements.items():
        value = value.replace(old, new)
    value = value.replace("\r", "\n")
    value = re.sub(r"[ ]{2,}", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def clean_inline_block_text(value: str) -> str:
    value = value.replace("A.\n", "A. ")
    value = value.replace("B.\n", "B. ")
    value = value.replace("C.\n", "C. ")
    value = value.replace("D.\n", "D. ")
    value = value.replace("E.\n", "E. ")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def extract_pdf_text(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    parts: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text:
            parts.append(text)
    return normalize_text("\n".join(parts))


def parse_legacy_questions(text: str, source_name: str) -> list[dict]:
    matches = list(LEGACY_QUESTION_START_RE.finditer(text))
    questions: list[dict] = []

    for index, match in enumerate(matches):
        prompt_number = int(match.group(1))
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        block = text[start:end].strip()

        answer_match = INLINE_ANSWER_RE.search(block)
        if not answer_match:
            continue

        answer_start = answer_match.start()
        question_body = block[:answer_start].strip()
        correct_option = answer_match.group(1).upper()

        prompt_label = match.group(0)
        question_body = question_body[len(prompt_label):].strip()
        first_option_start = re.search(r"(?:^|\n)A\.\s*", question_body)
        if not first_option_start:
            continue

        stem = clean_inline_block_text(question_body[: first_option_start.start()])
        options_block = question_body[first_option_start.start():].strip()
        option_matches = list(INLINE_OPTION_RE.finditer(options_block))
        options = build_inline_options(option_matches)
        if not is_valid_question(stem, options, correct_option):
            continue

        questions.append(build_question(prompt_number, source_name, stem, options, correct_option))

    return questions


def build_inline_options(option_matches: list[re.Match[str]]) -> list[dict]:
    options: list[dict] = []
    seen_option_keys: set[str] = set()
    for option_match in option_matches:
        key = option_match.group(1).upper()
        if key in seen_option_keys:
            continue
        seen_option_keys.add(key)
        option_text = clean_inline_block_text(option_match.group(2))
        options.append({"key": key, "text": option_text})
    return options


def parse_certyiq_questions(text: str, source_name: str) -> list[dict]:
    start_index = text.find("A team has just adopted an agile approach.")
    if start_index == -1:
        start_index = text.find("Question:")
    working_text = text[start_index:] if start_index != -1 else text
    working_text = re.sub(r"(?:Question:\s*\d+\s*Certy\s*IQ\s*)+", "\n", working_text, flags=re.IGNORECASE)
    working_text = re.sub(r"\bCerty\s*IQ\b", " ", working_text, flags=re.IGNORECASE)
    working_text = re.sub(r"([A-D])\.\s*\n", r"\1. ", working_text)

    block_pattern = re.compile(
        r"(?P<stem>.+?)\nA\.\s*(?P<a>.+?)\nB\.\s*(?P<b>.+?)\nC\.\s*(?P<c>.+?)\nD\.\s*(?P<d>.+?)\nAnswer:\s*(?P<answer>[A-D])",
        re.IGNORECASE | re.DOTALL,
    )

    questions: list[dict] = []
    for prompt_number, match in enumerate(block_pattern.finditer(working_text), start=1):
        stem = clean_inline_block_text(match.group("stem"))
        options = [
            {"key": "A", "text": clean_inline_block_text(match.group("a"))},
            {"key": "B", "text": clean_inline_block_text(match.group("b"))},
            {"key": "C", "text": clean_inline_block_text(match.group("c"))},
            {"key": "D", "text": clean_inline_block_text(match.group("d"))},
        ]
        correct_option = match.group("answer").upper()
        if not is_valid_question(stem, options, correct_option):
            continue
        questions.append(build_question(prompt_number, source_name, stem, options, correct_option))

    return questions


def parse_pmstudycircle_questions(text: str, source_name: str) -> list[dict]:
    answer_matches = {
        int(match.group(1)): match.group(2).upper() for match in PMSTUDY_ANSWER_RE.finditer(text)
    }
    if not answer_matches:
        return []

    answers_start = text.find("Answer-1:")
    working_text = text[:answers_start] if answers_start != -1 else text
    working_text = re.sub(r"Go to the Answer", "GO_TO_ANSWER", working_text, flags=re.IGNORECASE)
    question_pattern = re.compile(
        r"(?:^|\n)\s*Question:\s*(\d+)\s*(.+?)(?=(?:\n\s*Question:\s*\d+\s)|\Z)",
        re.IGNORECASE | re.DOTALL,
    )

    questions: list[dict] = []
    for match in question_pattern.finditer(working_text):
        prompt_number = int(match.group(1))
        block = match.group(2).strip()
        if "GO_TO_ANSWER" not in block:
            continue

        stem_match = re.match(r"(.+?)(?=\n\s*\(\s*a\s*\))", block, re.IGNORECASE | re.DOTALL)
        if not stem_match:
            continue

        stem = clean_inline_block_text(stem_match.group(1))
        option_matches = list(PMSTUDY_OPTION_RE.finditer(block))
        options = [
            {"key": option_match.group(1).upper(), "text": clean_inline_block_text(option_match.group(2))}
            for option_match in option_matches
        ]
        correct_option = answer_matches.get(prompt_number, "")
        if not is_valid_question(stem, options, correct_option):
            continue

        questions.append(build_question(prompt_number, source_name, stem, options, correct_option))

    return questions


def is_valid_question(stem: str, options: list[dict], correct_option: str) -> bool:
    if not stem:
        return False
    if re.search(r"\(\s*Choose\s+(two|three|four|\d+)\s*\.\s*\)", stem, re.IGNORECASE):
        return False
    if len(options) != 4:
        return False
    if correct_option not in {option["key"] for option in options}:
        return False
    return True


def build_question(prompt_number: int, source_name: str, stem: str, options: list[dict], correct_option: str) -> dict:
    return {
        "id": prompt_number,
        "promptNumber": prompt_number,
        "topic": "PMP",
        "source": source_name,
        "stem": stem,
        "options": options,
        "correctOption": correct_option,
    }


def parse_questions(text: str, source_name: str) -> list[dict]:
    for parser in (parse_legacy_questions, parse_certyiq_questions, parse_pmstudycircle_questions):
        questions = parser(text, source_name)
        if questions:
            return questions
    return []


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", nargs="+", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    all_questions: list[dict] = []
    next_id = 1

    for item in args.input:
        pdf_path = Path(item)
        text = extract_pdf_text(pdf_path)
        questions = parse_questions(text, pdf_path.name)
        for question in questions:
            question["id"] = next_id
            next_id += 1
            all_questions.append(question)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(
            {
                "title": "PMP Quiz Trainer",
                "batchSize": 20,
                "totalQuestions": len(all_questions),
                "questions": all_questions,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print(f"Extracted {len(all_questions)} questions to {output_path}")


if __name__ == "__main__":
    main()
