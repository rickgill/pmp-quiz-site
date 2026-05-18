from __future__ import annotations

import json
from functools import lru_cache
import re
from pathlib import Path

import fitz
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
QUESTIONS_PATH = ROOT / "data" / "questions.json"
PDF_PATH = Path(r"C:\pmp\drag and drop\110+Drag+&+Drop+Questions_David+McLachlan+2026.pdf")

BANK_ID = "drag-drop-david-mclachlan-111"
BANK_TITLE = "Drag & Drop PMP 111"
BANK_SOURCE = PDF_PATH.name

HEADER_WORDS = {
    "Answer",
    "Description",
    "Technique",
    "Chart",
    "Term",
    "Tool",
    "Method",
    "Stage",
    "Role",
    "PMO",
    "Style",
    "Category",
    "Theory",
    "Output",
    "Process",
    "Equation",
    "Ceremony",
    "Order",
    "Methodology",
}

REFERENCE_MARKERS = (
    "PMBOK Guide",
    "Process Groups:",
    "Agile Practice Guide",
    "Project Management:",
)

LABEL_STOPWORDS = {"and", "or", "to", "of", "in", "on", "at", "for", "the", "a", "an", "with"}

SPECIAL_PAIRS: dict[int, list[tuple[str, str]]] = {
    6: [
        ("The team update User Stories with acceptance criteria and estimates", "Backlog Refinement"),
        ("The team reflect on their process and lessons learnt", "Retrospective"),
        ("The team agree on User Stories to complete in the sprint", "Sprint Planning"),
        ("The team meet to update what they worked on yesterday, what they will do today and raise any blockers", "Daily Stand-ups"),
        ("The team demonstrate the usable increment to the customer", "Sprint Review"),
    ],
    10: [
        ("The PMO provides a consultative role to projects, supplies templates and best practices.", "Supportive"),
        ("The PMO requires compliance through adoption of methods or frameworks.", "Controlling"),
        ("Assigns Project Managers who report directly to the PMO.", "Directive"),
    ],
    11: [
        ("Resource availability high. Budget managed by Project Manager", "PMO"),
        ("Resource availability moderate to high. Budget managed by Project Manager", "Matrix - Strong"),
        ("Resource availability low. Budget managed by Functional Manager", "Matrix - Weak"),
        ("Resource availability low. Budget managed by Owner or Operator", "Organic"),
    ],
    12: [
        ("The Project Manager takes a hands-off approach, allows team to make own decisions", "Laissez-faire"),
        ("Focus on others' growth, learning, development, autonomy, and well-being", "Servant leader"),
        ("Inspirational motivation", "Transformational"),
        ("High energy, self-confident, holds strong convictions", "Charismatic"),
    ],
    14: [
        ("Project work is expanding to fit the time allocated to it", "Parkinson's Law"),
        ("The team waits until the last minute of a deadline to complete their work", "Student Syndrome"),
        ("The Functional Manager motivates people with things like money, bonuses and power", "Extrinsic Motivation"),
        ("When your team finds motivation in the work itself, through a strong purpose", "Intrinsic Motivation"),
        ("There is not a smooth transition between tasks or team members.", "Dropped Baton"),
    ],
    15: [
        ("Luke draws energy from solitary activities and inner reflection", "Introversion (I)"),
        ("Mike draws energy from social interaction and external activities", "Extraversion (E)"),
        ("Casey prefers focusing on concrete facts, details, and present realities", "Sensing (S)"),
        ("Sally prefers focusing on patterns, possibilities, and future-oriented ideas", "Intuition (N)"),
        ("Sofia makes decisions based on logical analysis and objective criteria", "Thinking (T)"),
        ("James makes decisions based on personal values, emotions, and empathy for others", "Feeling (F)"),
        ("Sarah prefers a flexible, adaptable, and spontaneous approach to life", "Perceiving (P)"),
        ("Jill prefers a planned, organized, and structured approach to life", "Judging (J)"),
    ],
    18: [
        ("Michael elicits requirements with the customer and monitors business value", "Business Analyst"),
        ("Penny oversees and coordinates multiple projects", "Program Manager"),
        ("Sofia is a manager, responsible for a particular area of the organization", "Functional Manager"),
        ("Ashley is responsible for the day-to-day workings of the company", "Operations Manager"),
    ],
    20: [
        ("The organization applies Scrum ways of working to programs and portfolios, only when necessary", "Large Scale Scrum"),
        ('The company focuses on organizing project teams around "Value Streams"', "SAFe"),
        ("A small team uses a framework that emphasizes iterative development, real customer involvement, and shared code", "Extreme Programming (XP)"),
        ("The team focuses on constraint-driven delivery and formalized prioritization of scope", "DSDM (Dynamic Systems Delivery Method)"),
    ],
    21: [
        ("First", "Stakeholder raises a change request"),
        ("Second", "Project team analyses the impact of the change"),
        ("Third", "Submit the change for approval (e.g. to CCB)"),
        ("Fourth", "Communicate the outcome of the request"),
        ("Fifth", "Record the outcome and close the item in the change log"),
    ],
    22: [
        ("First", "Identify risks"),
        ("Second", "Note risk likelihood and impact (Qualitative)"),
        ("Third", "Note additional risk data (Quantitative)"),
        ("Fourth", "Note risk responses and owners"),
        ("Fifth", "Implement responses if risks occur"),
    ],
    25: [
        ("Scope", "Adaptive: Variable in an Agile Project | Predictive: Fixed in a Predictive Project"),
        ("Cost", "Adaptive: Fixed in an Agile Project | Predictive: Variable in a Predictive Project"),
        ("Time", "Adaptive: Fixed in an Agile Project | Predictive: Variable in a Predictive Project"),
        ("Quality", "Adaptive: Fixed or Variable in an Agile Project | Predictive: Fixed or Variable in a Predictive Project"),
    ],
    27: [
        ("Communication Styles Assessment", "Plan Communications Management"),
        ("Team Charter", "Plan Resource Management"),
        ("Test and Inspection Planning", "Plan Scope Management"),
        ("Resource Breakdown Structure", "Estimate Resources"),
    ],
    29: [
        ("Individuals and interactions", "Processes and tools"),
        ("Working software", "Comprehensive documentation"),
        ("Customer collaboration", "Contract Negotiation"),
        ("Responding to change", "Following a plan"),
    ],
    31: [
        ("The Project Sponsor approves the Project Charter, and the PM Identifies the project Stakeholders", "Initiating"),
        ("The Project Manager develops the Project Management Plan, the team collect requirements and define the scope", "Planning"),
        ("The team manages project knowledge, acquire the resources for the project and implement risk responses", "Executing"),
        ("The project Customer validates the project scope based on the quality test outcomes", "Monitoring & Controlling"),
        ("The Project Manager creates the Final Report and releases project team members", "Closing"),
    ],
    33: [
        ("A Project Manager is working to Acquire Resources", "Project Team Assignments"),
        ("The project manager sees gaps in the team's work and needs to Develop the Team", "Team Performance Assessments"),
        ("A business analyst is facilitating a session to Identify Stakeholders", "Stakeholder Register"),
        ("The project management team Directs and Manages the Project Work", "Project Management Information System"),
    ],
    36: [
        ("Olivia provides expert judgement on part of a system for a project", "Consulted"),
        ("Ben creates the system flow chart to show people how it works", "Responsible"),
        ("Sarah signs off on the Project Deliverable, approving it for release", "Accountable"),
        ("Front-line workers need to be told about changes to the system", "Informed"),
    ],
    58: [
        ("Applies Scrum ways of working to programs and portfolios, only when necessary", "Large Scale Scrum (LeSS)"),
        ('Focuses on organizing project teams around "Value Streams"', "SAFe"),
        ("A scaled approach where multiple Scrum teams collaborate through regular cross-team meetings", "Scrum of Scrums"),
        ("Aims to extend Scrum practices to the organizational level, aiming to align and integrate multiple teams", "Enterprise Scrum"),
        ("Framework that offers a comprehensive, flexible approach, integrating Agile and Lean methodologies", "Disciplined Agile"),
    ],
    60: [
        ("Poor user experience", "Involve actual users of the system early and showcase to customers in the Sprint Review"),
        ("Unclear requirements", "Ensure the Three Amigos collaborate regularly to create User Stories"),
        ("Unclear purpose for the team", "Workshop the Team Charter to align the Mission and high-level Features."),
        ("Unclear working agreements", "Workshop the Team Charter, DoR and DoD with the team"),
    ],
    68: [
        ("Clear real-world measures of the risk Impacts and Likelihoods", "Risk Definitions"),
        ("The person accountable for the risk and its outcome", "Risk Owners"),
        ("The controls, mitigations or other responses", "Risk Responses"),
        ("A list of risks, including title, impact, status, owners and responses", "Risk Register"),
    ],
    69: [
        ("Assesses stakeholders by their Power, Urgency and Legitimacy", "Salience Chart"),
        ("Prioritizes stakeholders according to their impact on and influence over your project", "Stakeholder Matrix"),
        ("Document that lists all project stakeholders, detailing their interests, influence, and impact on the project", "Stakeholder Register"),
        ("Classifies stakeholders by their current and desired level of support for the project", "Stakeholder Engagement Matrix"),
    ],
    73: [
        ("James needs to see project activities visually, as bars on a calendar", "Gantt Chart"),
        ("Dylan has brainstormed dozens of ideas and needs to group them into similar categories", "Affinity Diagram"),
        ("Hannah needs a count of defects shown on a bar chart so she can see the most occurring ones", "Histogram"),
        ("Matthew has a complex defect and needs to find the root cause", "Cause and Effect Diagram"),
        ("Mia is sequencing the project activities and finding their dependencies", "Schedule Network Diagram"),
    ],
    77: [
        ("First", "Create Scope Management Plan"),
        ("Second", "Collect Requirements"),
        ("Third", "Create Scope Statement"),
        ("Fourth", "Create Work Breakdown Structure"),
        ("Fifth", "Create Work Breakdown Structure Dictionary"),
        ("Sixth", "Create a List of Work Packages"),
    ],
    79: [
        ("First", "Business Case"),
        ("Second", "Project Charter"),
        ("Third", "Project Management Plan"),
        ("Fourth", "PMIS"),
        ("Fifth", "Final Report"),
    ],
    80: [
        ("Project is under budget", "CPI is 1.2"),
        ("Project is behind schedule", "SPI is 0.8"),
        ("Project is over budget", "CV is -50"),
        ("Project is ahead of schedule", "SV is 100"),
    ],
    82: [
        ("High rates of scrap", "Use Value Stream Mapping and Kanban Boards to visualize the work, identify and track issues."),
        ("Long Delays for Approvals", "Streamline approval decisions through fewer people, up to certain value thresholds"),
        ("Stakeholders not engaged", "Use feedback loops, check whether sufficient information is being shared"),
        ("Team members unsure of how to undertake work", "Add more guidance, training and verification steps."),
    ],
    92: [
        ("Plan Schedule Management", "Schedule Management Plan"),
        ("Sequence Activities", "Leads and Lags"),
        ("Develop Schedule", "Critical Path Method"),
        ("Define Activities", "Decomposition"),
        ("Sequence Activities", "Precedence Diagramming Method"),
    ],
    99: [
        ("Work not complete within Sprints", "Reduce User Story size, define the Definition of Done"),
        ("Team struggles with obstacles", "Ensure the servant leader / scrum master escalates, problem-solves or clears these obstacles."),
        ("No improvement in team process", "Hold retrospectives regularly with no more than three action items for next time"),
        ("Siloed teams or people", "Work with managers of external resources to dedicate them to the team"),
    ],
    101: [
        ("Significant number of changes to the project requirements and scope", "Stakeholders disagree with project objectives"),
        ("Review the Issue Register for individual stakeholder challenges, use surveys and interviews", "Dissatisfied Stakeholders"),
        ("Project team apply critical thinking and interpersonal skills", "Leadership from all members"),
        ("The project team adapts to changing situations and is resilient in the face of challenges", "High-performing team"),
    ],
    106: [
        ("Rough Order of Magnitude (ROM)", "-25% to +75%"),
        ("Preliminary Estimate", "-15% to +50%"),
        ("Budget Estimate", "-10% to +25%"),
        ("Definitive Estimate", "-5% to +10%"),
        ("Final Estimate", "0%"),
    ],
    107: [
        ("Variable Cost", "Fixed Cost"),
        ("Directing Leadership", "Servant Leadership"),
        ("Prefer written communication", "Prefer face-to-face communication"),
        ("Requirements defined at beginning", "Requirements progressively elaborated"),
    ],
}


def normalize_text(value: str) -> str:
    value = value.replace(" \n", "\n")
    value = value.replace("\r", "\n")
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\s*-\s*", "-", value)
    value = re.sub(r"\n{2,}", "\n", value)
    return value.strip()


def clean_text(value: str) -> str:
    value = normalize_text(value)
    value = value.replace("Daily Standblockers-ups", "Daily Stand-ups")
    value = value.replace("Daily Stand - ups", "Daily Stand-ups")
    value = value.replace("Daily Stand- ups", "Daily Stand-ups")
    return value


def collect_rows(page) -> list[tuple[float, float, str]]:
    rows: list[tuple[float, float, str]] = []

    def visitor(text, cm, tm, font_dict, font_size):
        if text and text.strip():
            rows.append((round(tm[4], 1), round(tm[5], 1), text.strip().replace("\n", " ")))

    page.extract_text(visitor_text=visitor)
    return sorted(rows, key=lambda item: (-item[1], item[0]))


def is_reference_fragment(x: float, text: str) -> bool:
    text = clean_text(text)
    if x < 360 and any(marker in text for marker in REFERENCE_MARKERS):
        return True
    if x < 360 and re.match(r"^(P|p)\d+", text):
        return True
    if x < 360 and text in {"th", "Edition,", "Edition", ", 2017,", ", 2021,", ", 2023,", "2025,"}:
        return True
    return False


def merge_same_y_rows(rows: list[tuple[float, float, str]]) -> list[tuple[float, float, str]]:
    merged: list[tuple[float, float, str]] = []
    bucket: list[tuple[float, float, str]] = []

    def flush() -> None:
        nonlocal bucket
        if not bucket:
            return
        for cluster in split_x_clusters(bucket):
            y = cluster[0][1]
            x = min(item[0] for item in cluster)
            text = clean_text(" ".join(text for _, _, text in sorted(cluster, key=lambda item: item[0])))
            merged.append((x, y, text))
        bucket = []

    for row in rows:
        if not bucket or abs(bucket[0][1] - row[1]) <= 1.2:
            bucket.append(row)
        else:
            flush()
            bucket.append(row)

    flush()
    return merged


def split_x_clusters(rows: list[tuple[float, float, str]]) -> list[list[tuple[float, float, str]]]:
    clusters: list[list[tuple[float, float, str]]] = []
    for row in sorted(rows, key=lambda item: item[0]):
        if not clusters or row[0] - clusters[-1][-1][0] > 220:
            clusters.append([row])
        else:
            clusters[-1].append(row)
    return clusters


def is_label_like(text: str) -> bool:
    words = text.split()
    if not words:
        return False
    if len(words) <= 4:
        return True
    if "(" in text and ")" in text:
        return True
    if text == text.title():
        return True
    return False


def is_answer_phrase(text: str) -> bool:
    text = clean_text(text)
    if text.startswith("="):
        return False
    if "(" in text and ")" in text:
        return True
    if text == text.title():
        return True
    words = re.findall(r"[A-Za-z0-9'/&]+(?:-[A-Za-z0-9'/&]+)?", text)
    if not words:
        return False
    significant = [word for word in words if word.lower() not in LABEL_STOPWORDS]
    if not significant:
        return False
    if len(words) <= 6 and all(word[0].isupper() or word[0].isdigit() or word in {"&"} for word in significant):
        return True
    return False


def is_reference_line(x: float, text: str) -> bool:
    if text.startswith("© David McLachlan") or text.startswith("Â© David McLachlan"):
        return True
    if is_reference_fragment(x, text):
        return True
    if x < 360 and any(token in text for token in ("Edition", "Table")):
        return True
    return False


def parse_headers(raw_text: str) -> tuple[str, str]:
    for line in raw_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("Question "):
            continue
        parts = [part.strip() for part in re.split(r"\s{2,}", stripped) if part.strip()]
        if len(parts) == 2 and all(part in HEADER_WORDS for part in parts):
            return parts[0], parts[1]
    return "Prompt", "Answer"


def score_split(lines: list[tuple[int, str]], split_index: int) -> tuple[str, str, int]:
    prompt_text = clean_text(" ".join(text for _, text in lines[:split_index]))
    answer_text = clean_text(" ".join(text for _, text in lines[split_index:]))
    prompt_indent = sum(indent for indent, _ in lines[:split_index]) / len(lines[:split_index])
    answer_indent = sum(indent for indent, _ in lines[split_index:]) / len(lines[split_index:])

    score = 0
    if is_label_like(answer_text):
        score += 20
    else:
        score -= 20
    if is_label_like(prompt_text):
        score -= 8
    if len(answer_text) < len(prompt_text):
        score += 3
    if len(answer_text.split()) > 8:
        score -= 12
    if len(prompt_text.split()) <= 2:
        score -= 4
    if answer_indent >= prompt_indent:
        score += 2

    return prompt_text, answer_text, score


def segment_layout_lines(lines: list[tuple[int, str]]) -> list[tuple[str, str]]:
    max_block_size = min(4, len(lines))

    @lru_cache(maxsize=None)
    def solve(index: int) -> tuple[int, tuple[tuple[str, str], ...]]:
        if index >= len(lines):
            return 0, ()

        best_score = -10**9
        best_pairs: tuple[tuple[str, str], ...] = ()
        remaining = len(lines) - index

        for block_size in range(2, min(max_block_size, remaining) + 1):
            block = lines[index : index + block_size]
            for split_index in range(1, block_size):
                prompt_text, answer_text, score = score_split(block, split_index)
                tail_score, tail_pairs = solve(index + block_size)
                total_score = score + tail_score - 1
                if total_score > best_score:
                    best_score = total_score
                    best_pairs = ((prompt_text, answer_text),) + tail_pairs

        return best_score, best_pairs

    return list(solve(0)[1])


def parse_reference_mixed_line(line: str) -> list[str]:
    parts = [part.strip() for part in re.split(r"\s{5,}", line) if part.strip()]
    if len(parts) <= 1:
        return [line]

    kept = []
    for part in parts:
        if any(marker in part for marker in REFERENCE_MARKERS):
            continue
        if re.match(r"^(P|p)\d+", part):
            continue
        if "© David McLachlan" in part or "Â© David McLachlan" in part:
            continue
        kept.append(part)
    return kept or [line]


def clean_block_lines(text: str) -> str:
    kept: list[str] = []
    for line in text.splitlines():
        item = clean_text(line)
        if not item:
            continue
        if item.startswith("Question "):
            continue
        if item in HEADER_WORDS:
            continue
        if item.startswith("© David McLachlan") or item.startswith("Â© David McLachlan"):
            continue
        if re.fullmatch(r"\d+", item):
            continue
        if any(marker in item for marker in REFERENCE_MARKERS):
            continue
        if re.match(r"^(P|p)\d+", item):
            continue
        if item in {"Edition, 2021,", "Edition 2025,", "Table”.", ", 2023", ", 2021", ", 2017"}:
            continue
        kept.append(item)
    return clean_text(" ".join(kept))


def should_skip_line(text: str) -> bool:
    if not text:
        return True
    if text.startswith("Question "):
        return True
    if text in HEADER_WORDS:
        return True
    if text.startswith("Â© David McLachlan") or text.startswith("Ã‚Â© David McLachlan"):
        return True
    if re.fullmatch(r"\d+", text):
        return True
    if any(marker in text for marker in REFERENCE_MARKERS):
        return True
    if re.match(r"^(P|p)\d+", text):
        return True
    if re.search(r"(Edition|Table)", text) and len(text.split()) <= 6:
        return True
    return False


def merge_wrapped_items(lines: list[tuple[float, float, float, str]]) -> list[tuple[float, float, float, str]]:
    if not lines:
        return []

    merged: list[tuple[float, float, float, str]] = [lines[0]]
    for x0, y0, width, text in lines[1:]:
        last_x0, last_y0, last_width, last_text = merged[-1]
        close_y = y0 - last_y0 <= 26
        similar_x = abs(x0 - last_x0) <= 90
        if close_y and similar_x and last_text not in {"First", "Second", "Third", "Fourth", "Fifth", "Sixth", "Seventh", "Eighth", "Ninth", "Tenth"} and (
            text.startswith("(")
            or last_text.endswith(("of", "and", "to", "the", "with", "for", "-"))
            or (is_answer_phrase(last_text) and is_answer_phrase(text))
        ):
            merged[-1] = (min(last_x0, x0), last_y0, max(last_width, width), clean_text(f"{last_text} {text}"))
        else:
            merged.append((x0, y0, width, text))
    return merged


def parse_ordinal_order_pairs(lines: list[tuple[float, float, float, str]]) -> list[tuple[str, str]]:
    ordinal_words = {"First", "Second", "Third", "Fourth", "Fifth", "Sixth", "Seventh", "Eighth", "Ninth", "Tenth"}
    items = merge_wrapped_items(lines)
    pairs: list[tuple[str, str]] = []
    current_label: str | None = None
    current_parts: list[str] = []

    for _, _, _, text in items:
        if text in ordinal_words:
            if current_label and current_parts:
                pairs.append((current_label, clean_text(" ".join(current_parts))))
            current_label = text
            current_parts = []
        elif current_label:
            current_parts.append(text)

    if current_label and current_parts:
        pairs.append((current_label, clean_text(" ".join(current_parts))))
    return pairs


def parse_consecutive_pairs(lines: list[tuple[float, float, float, str]]) -> list[tuple[str, str]]:
    items = merge_wrapped_items(lines)
    texts = [text for _, _, _, text in items]
    if len(texts) % 2 != 0:
        raise ValueError("odd number of consecutive pair items")
    return [(texts[index], texts[index + 1]) for index in range(0, len(texts), 2)]


def parse_two_column_compare(lines: list[tuple[float, float, float, str]]) -> list[tuple[str, str]]:
    filtered = [item for item in lines if item[3] not in {"Predictive", "Agile", "Adaptive"}]
    left = merge_wrapped_items([item for item in filtered if item[0] < 650])
    right = merge_wrapped_items([item for item in filtered if item[0] >= 650])
    left_texts = [text for _, _, _, text in left]
    right_texts = [text for _, _, _, text in right]
    return list(zip(left_texts, right_texts))


def parse_alternating_answer_description(lines: list[tuple[float, float, float, str]]) -> list[tuple[str, str]]:
    items = merge_wrapped_items(lines)
    pairs: list[tuple[str, str]] = []
    current_answer: str | None = None
    current_desc: list[str] = []

    for x0, _, width, text in items:
        answer_like = is_answer_phrase(text) and x0 >= 560 and width <= 280
        if answer_like:
            if current_answer and current_desc:
                pairs.append((clean_text(" ".join(current_desc)), current_answer))
                current_desc = []
            current_answer = text
        else:
            current_desc.append(text)

    if current_answer and current_desc:
        pairs.append((clean_text(" ".join(current_desc)), current_answer))
    return pairs


def parse_answer_pairs(pdf_page, left_label: str, right_label: str, prompt_number: int) -> list[tuple[str, str]]:
    if prompt_number == 111:
        return [
            ("Prefers solitary activities", "Introversion (I)"),
            ("Enjoys social interaction", "Extraversion (E)"),
            ("Use their senses to determine reality", "Sensing (S)"),
            ("Use intuition to find patterns", "Intuition (N)"),
            ("Are logical and impersonal", "Thinking (T)"),
            ("Focus on feelings and emotions", "Feeling (F)"),
            ("Judge with firm fast decisions", "Judging (J)"),
            ("Perceive with a flexible and adaptable approach", "Perceiving (P)"),
        ]

    lines: list[tuple[float, float, float, str]] = []
    page_dict = pdf_page.get_text("dict")
    for block in page_dict.get("blocks", []):
        for line in block.get("lines", []):
            x0, y0, x1, y1 = line["bbox"]
            if y0 < 90 or y0 > 560:
                continue
            text = clean_text("".join(span["text"] for span in line["spans"]))
            if should_skip_line(text):
                continue
            lines.append((x0, y0, x1 - x0, text))

    lines.sort(key=lambda item: (item[1], item[0]))

    if prompt_number in {15, 25, 85, 86, 90, 91, 107}:
        return parse_two_column_compare(lines)

    if any(text in {"First", "Second", "Third", "Fourth", "Fifth", "Sixth", "Seventh", "Eighth", "Ninth", "Tenth"} for _, _, _, text in lines):
        return parse_ordinal_order_pairs(lines)

    all_label_lines = all(is_answer_phrase(text) for _, _, _, text in lines)
    if all_label_lines:
        return parse_consecutive_pairs(lines)

    if prompt_number in {80, 99, 101}:
        return parse_alternating_answer_description(lines)

    pairs: list[tuple[str, str]] = []
    prompt_parts: list[str] = []
    answer_parts: list[str] = []

    def is_answer_block(x0: float, width: float, text: str) -> bool:
        if text.startswith("("):
            return True
        if not is_answer_phrase(text):
            return False
        return x0 >= 550 and width <= 280

    def finalize_pair() -> None:
        nonlocal prompt_parts, answer_parts
        if prompt_parts and answer_parts:
            pairs.append((clean_text(" ".join(prompt_parts)), clean_text(" ".join(answer_parts))))
        prompt_parts = []
        answer_parts = []

    for x0, _, width, text in lines:
        answer_like = is_answer_block(x0, width, text)
        if not prompt_parts:
            prompt_parts.append(text)
            continue

        if not answer_parts:
            if answer_like:
                answer_parts.append(text)
            else:
                prompt_parts.append(text)
            continue

        if answer_like:
            answer_parts.append(text)
            continue

        finalize_pair()
        prompt_parts.append(text)

    finalize_pair()
    return pairs


def build_question(prompt_number: int, title: str, left_label: str, right_label: str, pairs: list[tuple[str, str]]) -> dict:
    prompt_items = [{"id": f"p{index+1}", "text": prompt} for index, (prompt, _) in enumerate(pairs)]
    choice_items = [{"id": f"c{index+1}", "text": answer} for index, (_, answer) in enumerate(pairs)]
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
        "leftLabel": right_label,
        "rightLabel": left_label,
        "prompts": prompt_items,
        "choices": choice_items,
        "correctMatches": correct_matches,
    }


def build_special_question(prompt_number: int, title: str, left_label: str, right_label: str) -> dict:
    return build_question(prompt_number, title, left_label, right_label, SPECIAL_PAIRS[prompt_number])


def parse_question(question_page, answer_page, fitz_answer_page) -> dict | None:
    raw_text = question_page.extract_text() or ""
    title_match = re.search(r"Question\s+(\d+):\s*(.+)", raw_text)
    if not title_match:
        return None

    prompt_number = int(title_match.group(1))
    title = clean_text(title_match.group(2))
    left_label, right_label = parse_headers(answer_page.extract_text(extraction_mode="layout") or "")

    if prompt_number in SPECIAL_PAIRS:
        return build_special_question(prompt_number, title, left_label, right_label)

    pairs = parse_answer_pairs(fitz_answer_page, left_label, right_label, prompt_number)

    if len(pairs) < 2:
        raise ValueError(f"Unable to parse question {prompt_number}: only {len(pairs)} answer pairs")

    return build_question(prompt_number, title, left_label, right_label, pairs)


def build_bank() -> dict:
    reader = PdfReader(str(PDF_PATH))
    fitz_doc = fitz.open(str(PDF_PATH))
    questions = []
    for page_index in range(4, len(reader.pages), 2):
        parsed = parse_question(reader.pages[page_index], reader.pages[page_index + 1], fitz_doc[page_index + 1])
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
