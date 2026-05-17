from __future__ import annotations

import json
import re
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
QUESTIONS_PATH = ROOT / "data" / "questions.json"
PDF_PATH = Path(r"C:\pmp\drag and drop\110+Drag+&+Drop+Questions_David+McLachlan+2026.pdf")

BANK_ID = "drag-drop-david-mclachlan-111"
BANK_TITLE = "Drag & Drop PMP 111"
BANK_SOURCE = PDF_PATH.name

SPECIAL_GROUP_QUESTIONS = {
    85: {
        "title": "Predictive and Adaptive",
        "choices": [
            "Fixed Scope and Requirements",
            "Adaptive Planning",
            "Incremental Delivery",
            "Sequential Phases",
            "Detailed Planning",
            "Cross-Functional Teams",
        ],
        "groups": {
            "Predictive": [
                "Fixed Scope and Requirements",
                "Sequential Phases",
                "Detailed Planning",
            ],
            "Agile": [
                "Adaptive Planning",
                "Incremental Delivery",
                "Cross-Functional Teams",
            ],
        },
    },
    86: {
        "title": "Predictive and Adaptive",
        "choices": [
            "Product Backlog",
            "Sprint Backlog",
            "Work Breakdown Structure (WBS)",
            "Change Management Plan",
            "Risk Management Plan",
            "Burndown Chart",
        ],
        "groups": {
            "Predictive": [
                "Work Breakdown Structure (WBS)",
                "Change Management Plan",
                "Risk Management Plan",
            ],
            "Agile": [
                "Product Backlog",
                "Sprint Backlog",
                "Burndown Chart",
            ],
        },
    },
    90: {
        "title": "Predictive versus Adaptive",
        "choices": [
            "Scope is Fixed",
            "Scope is Variable",
            "Scope Management Plan",
            "Product Backlog",
            "Epics and User Stories",
            "Deliverables and Work Packages",
        ],
        "groups": {
            "Predictive": [
                "Scope is Fixed",
                "Scope Management Plan",
                "Deliverables and Work Packages",
            ],
            "Agile": [
                "Scope is Variable",
                "Product Backlog",
                "Epics and User Stories",
            ],
        },
    },
    107: {
        "title": "Adaptive versus Predictive",
        "choices": [
            "Variable Cost",
            "Fixed Cost",
            "Servant Leadership",
            "Directing Leadership",
            "Prefer written communication",
            "Prefer face-to-face communication",
            "Requirements defined at beginning",
            "Requirements progressively elaborated",
        ],
        "groups": {
            "Predictive": [
                "Variable Cost",
                "Directing Leadership",
                "Prefer written communication",
                "Requirements defined at beginning",
            ],
            "Agile": [
                "Fixed Cost",
                "Servant Leadership",
                "Prefer face-to-face communication",
                "Requirements progressively elaborated",
            ],
        },
    },
}

SPECIAL_PAIR_QUESTION_111 = {
    "title": "Team Personality Assessment",
    "pairs": [
        ("Prefers solitary activities", "Introversion (I)"),
        ("Enjoys social interaction", "Extraversion (E)"),
        ("Use their senses to determine reality", "Sensing (S)"),
        ("Use intuition to find patterns", "Intuition (N)"),
        ("Are logical and impersonal", "Thinking (T)"),
        ("Focus on feelings and emotions", "Feeling (F)"),
        ("Judge with firm fast decisions", "Judging (J)"),
        ("Perceive with a flexible and adaptable approach", "Perceiving (P)"),
    ],
}


def normalize_text(value: str) -> str:
    value = value.replace(" \n", "\n")
    value = value.replace("\r", "\n")
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\s*-\s*", "-", value)
    value = re.sub(r"\n{2,}", "\n", value)
    return value.strip()


def collect_rows(page) -> list[tuple[float, float, str]]:
    rows: list[tuple[float, float, str]] = []

    def visitor(text, cm, tm, font_dict, font_size):
        if text and text.strip():
            rows.append((round(tm[4], 1), round(tm[5], 1), text.strip().replace("\n", " ")))

    page.extract_text(visitor_text=visitor)
    return sorted(rows, key=lambda item: (-item[1], item[0]))


def group_entries(rows: list[tuple[float, float, str]], min_x: float, max_x: float) -> list[str]:
    filtered = [
        (x, y, text)
        for x, y, text in rows
        if min_x <= x <= max_x and 40 < y < 530 and not text.startswith("©") and text not in {"5", "7"}
    ]

    groups: list[dict] = []
    for x, y, text in filtered:
        if text in {"Description", "Answer", "Technique", "Chart", "Term", "Tool", "Method", "Stage", "Role", "PMO", "Style", "Category", "Theory", "Stage", "Output", "Process", "Equation", "Ceremony", "Order"}:
            continue

        if groups and abs(groups[-1]["last_y"] - y) <= 26:
            groups[-1]["parts"].append(text)
            groups[-1]["last_y"] = y
        else:
            groups.append({"last_y": y, "parts": [text]})

    return [normalize_text(" ".join(group["parts"])) for group in groups if normalize_text(" ".join(group["parts"]))]


def should_merge_left(existing: str, incoming: str) -> bool:
    if not existing:
        return False
    if existing.endswith("-"):
        return True
    if existing.split()[-1].lower() in {"to", "and", "of", "the", "with", "for"}:
        return True
    if incoming.isupper():
        return False
    if len(existing.split()) >= 2 and len(incoming.split()) <= 2 and len(existing.split()) <= 3:
        return True
    return False


def parse_layout_entries(page) -> tuple[list[str], list[str]]:
    text = page.extract_text(extraction_mode="layout") or ""
    lines = text.splitlines()
    left_entries: list[str] = []
    right_entries: list[str] = []
    previous_pattern = ""
    seen_blank = False

    for line in lines:
        if not line.strip():
            seen_blank = True
            continue

        stripped = line.strip()
        if stripped.startswith("Question ") or stripped.startswith("© David McLachlan"):
            continue
        if re.fullmatch(
            r"(Answer|Technique|Chart|Term|Tool|Method|Stage|Role|PMO|Style|Category|Theory|Output|Ceremony)\s+"
            r"(Description|Equation|Order|Process)",
            stripped,
        ):
            continue
        if stripped in {
            "Answer Description",
            "Technique Description",
            "Chart Description",
            "Term Description",
            "Tool Description",
            "Method Description",
            "Stage Description",
            "Role Description",
            "PMO Description",
            "Style Description",
            "Category Description",
            "Theory Description",
            "Output Process",
            "Answer Equation",
            "Ceremony Order",
            "Stage Order",
        }:
            continue

        indent = len(line) - len(line.lstrip())
        parts = [part.strip() for part in re.split(r"\s{10,}", line.rstrip()) if part.strip()]
        if not parts:
            seen_blank = True
            continue

        if len(parts) >= 2:
            left_text = normalize_text(parts[0])
            right_text = normalize_text(" ".join(parts[1:]))
            if left_text:
                if left_entries and should_merge_left(left_entries[-1], left_text):
                    left_entries[-1] = normalize_text(f"{left_entries[-1]} {left_text}")
                else:
                    left_entries.append(left_text)

            if right_text:
                if right_entries and previous_pattern == "right_only" and not seen_blank:
                    right_entries[-1] = normalize_text(f"{right_entries[-1]} {right_text}")
                else:
                    right_entries.append(right_text)

            previous_pattern = "both"
            seen_blank = False
            continue

        text_part = normalize_text(parts[0])
        if indent >= 35:
            if right_entries and len(left_entries) > len(right_entries):
                right_entries.append(text_part)
            elif right_entries:
                right_entries[-1] = normalize_text(f"{right_entries[-1]} {text_part}")
            else:
                right_entries.append(text_part)
            previous_pattern = "right_only"
        else:
            if left_entries and previous_pattern == "both" and not seen_blank:
                left_entries[-1] = normalize_text(f"{left_entries[-1]} {text_part}")
            elif left_entries and should_merge_left(left_entries[-1], text_part):
                left_entries[-1] = normalize_text(f"{left_entries[-1]} {text_part}")
            else:
                left_entries.append(text_part)
            previous_pattern = "left_only"
        seen_blank = False

    return left_entries, right_entries


def parse_special_question_111(raw_text: str) -> tuple[list[str], list[str]]:
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    lines = [line for line in lines if not line.startswith("Question 111:") and line not in {"Tool Description"} and not line.startswith("©")]

    answers = []
    descriptions = []
    paired_answer_lines = []

    for line in lines:
        if any(token in line for token in ["(I)", "(E)", "(S)", "(N)", "(T)", "(F)", "(J)", "(P)"]):
            paired_answer_lines.append(line)
        else:
            descriptions.append(line)

    for line in paired_answer_lines:
        parts = re.split(r"\s{2,}", line)
        if len(parts) >= 2:
            answers.extend([part.strip() for part in parts if part.strip()])
        else:
            answers.extend(re.findall(r"[A-Za-z]+(?: [A-Za-z]+)* \([A-Z]\)", line))

    merged_descriptions: list[str] = []
    buffer = ""
    for line in descriptions:
        if not buffer:
            buffer = line
            continue
        if buffer.endswith(("to", "and", "with")) or len(buffer) < 28:
            buffer = f"{buffer} {line}"
        else:
            merged_descriptions.append(normalize_text(buffer))
            buffer = line
    if buffer:
        merged_descriptions.append(normalize_text(buffer))

    return answers, merged_descriptions


def build_group_question(prompt_number: int, title: str, groups: dict[str, list[str]], choices: list[str]) -> dict:
    prompt_items = [{"id": f"p{index+1}", "text": label} for index, label in enumerate(groups.keys())]
    choice_items = [{"id": f"c{index+1}", "text": text} for index, text in enumerate(choices)]
    choice_lookup = {item["text"]: item["id"] for item in choice_items}
    prompt_lookup = {item["text"]: item["id"] for item in prompt_items}

    correct_matches = []
    for label, texts in groups.items():
        for text in texts:
            correct_matches.append({"promptId": prompt_lookup[label], "choiceId": choice_lookup[text]})

    return {
        "id": prompt_number,
        "promptNumber": prompt_number,
        "topic": "Drag & Drop",
        "source": BANK_SOURCE,
        "type": "drag-drop-group",
        "stem": title,
        "leftLabel": "Choices",
        "rightLabel": "Groups",
        "prompts": prompt_items,
        "choices": choice_items,
        "correctMatches": correct_matches,
    }


def build_pair_question(prompt_number: int, title: str, pairs: list[tuple[str, str]]) -> dict:
    prompt_items = [{"id": f"p{index+1}", "text": left} for index, (left, _) in enumerate(pairs)]
    choice_items = [{"id": f"c{index+1}", "text": right} for index, (_, right) in enumerate(pairs)]
    correct_matches = [
        {"promptId": prompt_items[index]["id"], "choiceId": choice_items[index]["id"]}
        for index in range(len(pairs))
    ]

    return {
        "id": prompt_number,
        "promptNumber": prompt_number,
        "topic": "Drag & Drop",
        "source": BANK_SOURCE,
        "type": "drag-drop",
        "stem": title,
        "leftLabel": "Description",
        "rightLabel": "Tool",
        "prompts": prompt_items,
        "choices": choice_items,
        "correctMatches": correct_matches,
    }


def is_label_like(line: str) -> bool:
    words = line.split()
    if not words:
        return False
    if len(words) <= 4:
        return True
    if "(" in line and ")" in line:
        return True
    if line == line.title():
        return True
    return False


def derive_answers_from_raw(raw_text: str, answer_count: int) -> list[str]:
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    filtered = [
        line
        for line in lines
        if not line.startswith("Question ")
        and line not in {
            "Answer Description",
            "Technique Description",
            "Chart Description",
            "Term Description",
            "Tool Description",
            "Method Description",
            "Stage Description",
            "Role Description",
            "PMO Description",
            "Style Description",
            "Category Description",
            "Theory Description",
            "Output Process",
            "Answer Equation",
            "Ceremony Order",
            "Stage Order",
        }
        and not line.startswith("© David McLachlan")
    ]

    tail: list[str] = []
    for line in reversed(filtered):
        if is_label_like(line):
            tail.append(line)
        else:
            if tail:
                break

    candidates = list(reversed(tail))
    while len(candidates) > answer_count:
        merged = False
        for index in range(len(candidates) - 1):
            current_words = len(candidates[index].split())
            next_words = len(candidates[index + 1].split())
            if candidates[index].endswith("-") or next_words <= 2:
                candidates[index] = normalize_text(f"{candidates[index]} {candidates[index + 1]}")
                del candidates[index + 1]
                merged = True
                break
            if current_words <= 3 and next_words == 1:
                candidates[index] = normalize_text(f"{candidates[index]} {candidates[index + 1]}")
                del candidates[index + 1]
                merged = True
                break
        if not merged:
            candidates[-2] = normalize_text(f"{candidates[-2]} {candidates[-1]}")
            candidates.pop()

    return candidates


def parse_question(page_index: int, page) -> dict | None:
    raw_text = page.extract_text() or ""
    title_match = re.search(r"Question\s+(\d+):\s*(.+)", raw_text)
    if not title_match:
        return None

    prompt_number = int(title_match.group(1))
    title = normalize_text(title_match.group(2))

    if prompt_number in SPECIAL_GROUP_QUESTIONS:
        item = SPECIAL_GROUP_QUESTIONS[prompt_number]
        return build_group_question(prompt_number, item["title"], item["groups"], item["choices"])

    if prompt_number == 111:
        return build_pair_question(prompt_number, SPECIAL_PAIR_QUESTION_111["title"], SPECIAL_PAIR_QUESTION_111["pairs"])

    answers, descriptions = parse_layout_entries(page)
    if len(answers) != len(descriptions):
        answers = derive_answers_from_raw(raw_text, len(descriptions))

    if len(answers) != len(descriptions) or len(answers) < 2:
        raise ValueError(f"Unable to parse question {prompt_number}: {len(answers)} answers, {len(descriptions)} descriptions")

    prompt_items = [{"id": f"p{index+1}", "text": text} for index, text in enumerate(descriptions)]
    choice_items = [{"id": f"c{index+1}", "text": text} for index, text in enumerate(answers)]
    correct_matches = [
        {"promptId": prompt_items[index]["id"], "choiceId": choice_items[index]["id"]}
        for index in range(len(prompt_items))
    ]

    return {
        "id": prompt_number,
        "promptNumber": prompt_number,
        "topic": "Drag & Drop",
        "source": BANK_SOURCE,
        "type": "drag-drop",
        "stem": title,
        "leftLabel": "Description",
        "rightLabel": "Answer",
        "prompts": prompt_items,
        "choices": choice_items,
        "correctMatches": correct_matches,
    }


def build_bank() -> dict:
    reader = PdfReader(str(PDF_PATH))
    questions = []
    for page_index in range(4, len(reader.pages), 2):
        parsed = parse_question(page_index, reader.pages[page_index])
        if parsed:
            questions.append(parsed)

    return {
        "id": BANK_ID,
        "title": BANK_TITLE,
        "source": BANK_SOURCE,
        "totalQuestions": len(questions),
        "questions": questions,
    }


def update_questions_json() -> None:
    payload = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    banks = payload.get("banks", [])
    new_bank = build_bank()

    replaced = False
    for index, bank in enumerate(banks):
        if bank.get("id") == BANK_ID:
            banks[index] = new_bank
            replaced = True
            break

    if not replaced:
        banks.append(new_bank)

    payload["banks"] = banks
    payload["totalQuestions"] = sum(len(bank.get("questions", [])) for bank in banks)
    QUESTIONS_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Updated {QUESTIONS_PATH} with bank '{BANK_TITLE}' ({new_bank['totalQuestions']} questions).")


if __name__ == "__main__":
    update_questions_json()
