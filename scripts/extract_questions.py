from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from pypdf import PdfReader


QUESTION_START_RE = re.compile(r"Topic\s+\d+Question\s+#(\d+)", re.IGNORECASE)
OPTION_RE = re.compile(r"(?:^|\n)([A-E])\.\s*(.+?)(?=(?:\n[A-E]\.\s)|(?:\nCorrect\s*Answer\s*:)|\Z)", re.DOTALL)
ANSWER_RE = re.compile(r"Correct\s*Answer\s*:\s*([A-E])", re.IGNORECASE)


def normalize_text(value: str) -> str:
    replacements = {
        "\x00": "fi",
        "\u00a0": " ",
        "\uf013": " ",
        "\uf017": " ",
        "\uf007": " ",
        "\uf147": " ",
        "\uf164": " ",
    }
    for old, new in replacements.items():
        value = value.replace(old, new)
    value = value.replace("\r", "\n")
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def extract_pdf_text(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    parts: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text:
            parts.append(text)
    return normalize_text("\n".join(parts))


def parse_questions(text: str, source_name: str) -> list[dict]:
    matches = list(QUESTION_START_RE.finditer(text))
    questions: list[dict] = []

    for index, match in enumerate(matches):
      prompt_number = int(match.group(1))
      start = match.start()
      end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
      block = text[start:end].strip()

      answer_match = ANSWER_RE.search(block)
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

      stem = question_body[: first_option_start.start()].strip()
      options_block = question_body[first_option_start.start():].strip()
      option_matches = list(OPTION_RE.finditer(options_block))
      if len(option_matches) < 2:
          continue

      stem = re.sub(r"\s+", " ", stem)
      if re.search(r"\(\s*Choose\s+(two|three|four|\d+)\s*\.\s*\)", stem, re.IGNORECASE):
          continue
      options = []
      seen_option_keys: set[str] = set()
      for option_match in option_matches:
          key = option_match.group(1).upper()
          if key in seen_option_keys:
              continue
          seen_option_keys.add(key)
          option_text = re.sub(r"\s+", " ", option_match.group(2)).strip()
          options.append({"key": key, "text": option_text})

      if len(options) != 4:
          continue

      if correct_option not in {option["key"] for option in options}:
          continue

      questions.append(
          {
              "id": prompt_number,
              "promptNumber": prompt_number,
              "topic": "PMP",
              "source": source_name,
              "stem": stem,
              "options": options,
              "correctOption": correct_option,
          }
      )

    return questions


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", nargs="+", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    all_questions: list[dict] = []
    seen_ids: set[int] = set()

    for item in args.input:
        pdf_path = Path(item)
        text = extract_pdf_text(pdf_path)
        questions = parse_questions(text, pdf_path.name)
        for question in questions:
            if question["id"] in seen_ids:
                continue
            seen_ids.add(question["id"])
            all_questions.append(question)

    all_questions.sort(key=lambda item: item["promptNumber"])

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
