from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
QUESTIONS_PATH = ROOT / "data" / "questions.json"

SOURCE_BANK_ID = "web-curated-pmbok7-200"
BANK_ID = "top-200-non-business"
BANK_TITLE = "Top 200 PMP People + Process"
BANK_SOURCE = "Original non-business PMP bank compiled from PMI-aligned research and curated practice themes (May 19, 2026)"

EXCLUDED_TOPICS = {"Value & Business", "AI & Sustainability"}
OPTION_KEYS = ["A", "B", "C", "D"]


def q(topic: str, stem: str, correct: str, d1: str, d2: str, d3: str) -> tuple[str, str, str, list[str]]:
    return topic, stem, correct, [d1, d2, d3]


SUPPLEMENTAL_BLUEPRINTS: list[tuple[str, str, str, list[str]]] = [
    q(
        "Approach & Life Cycle",
        "A project has fixed regulatory deliverables, but the user experience will need rapid refinement after pilots. Which approach is best?",
        "Use a hybrid approach with predictive control for regulated outputs and adaptive delivery for user-facing features.",
        "Use a fully predictive approach so all work follows one baseline.",
        "Use a fully agile approach and avoid any formal milestones.",
        "Delay selecting an approach until half the work is complete.",
    ),
    q(
        "Adaptability & Change",
        "A stakeholder proposes a major feature during execution on a predictive project. What should the project manager do first?",
        "Assess the impact across scope, schedule, cost, quality, risk, and resources before seeking approval through change control.",
        "Ask the team to begin the feature immediately to preserve stakeholder trust.",
        "Reject the idea because baselines cannot change after approval.",
        "Move the request into lessons learned for future projects.",
    ),
    q(
        "Uncertainty",
        "A risk response owner says a high-priority threat is becoming more likely because a supplier keeps missing readiness checkpoints. What should happen next?",
        "Reassess the risk, update the register, and execute the agreed response or contingency if trigger conditions are met.",
        "Wait until the risk becomes an issue before taking action.",
        "Transfer the risk to the quality team because checkpoints are involved.",
        "Close the risk because the root cause is outside the project team.",
    ),
    q(
        "Team",
        "A cross-functional team depends on one specialist who has become a bottleneck. Which action best improves long-term performance?",
        "Promote knowledge sharing and cross-training so dependency on one person is reduced.",
        "Ask the specialist to work overtime until the release is complete.",
        "Hide the bottleneck from stakeholders to protect team morale.",
        "Freeze all new work until a second specialist is hired.",
    ),
    q(
        "Stakeholders",
        "A sponsor wants weekly summaries, but operational users need brief daily updates during cutover week. What should the project manager do?",
        "Tailor communication cadence and detail to each stakeholder group's decision needs.",
        "Send the weekly sponsor summary to all stakeholders to keep reporting consistent.",
        "Send daily updates only, because more frequent communication is always better.",
        "Stop reporting during cutover to let the team focus on delivery.",
    ),
    q(
        "Planning",
        "A project manager is estimating a complex work package with limited historical data. What is the best first step?",
        "Decompose the work and involve knowledgeable team members to improve estimating accuracy.",
        "Assign the average estimate from unrelated prior projects.",
        "Use the most optimistic estimate to protect the business case.",
        "Skip estimation until execution begins and actuals are available.",
    ),
    q(
        "Measurement",
        "A predictive project has EV = 80 and PV = 100 midway through the phase. What does this indicate?",
        "The project is behind schedule because earned value is lower than planned value.",
        "The project is ahead of schedule because earned value exceeds actual cost.",
        "The project is under budget because planned value is higher than earned value.",
        "The data is insufficient because schedule performance cannot be evaluated from EV and PV.",
    ),
    q(
        "Measurement",
        "A project has EV = 90 and AC = 110. What should the project manager conclude?",
        "The project is over budget because actual cost exceeds earned value.",
        "The project is ahead of schedule because earned value is high.",
        "The project is under budget because cost has already been spent.",
        "No conclusion can be drawn until planned value is known.",
    ),
    q(
        "Delivery",
        "During sprint review, stakeholders ask for a reprioritization rather than immediate addition of every new idea. What should the project manager support?",
        "Capture the feedback and let the product owner reorder the backlog based on value and capacity.",
        "Add every new request directly into the current sprint to maximize responsiveness.",
        "Reject all new ideas until the release is complete.",
        "Escalate every suggestion to the sponsor before the product owner reviews it.",
    ),
    q(
        "Approach & Life Cycle",
        "Which project characteristic most strongly favors an adaptive approach?",
        "Requirements are expected to evolve through frequent stakeholder feedback.",
        "The solution must follow a fixed design approved before work begins.",
        "Work cannot be delivered incrementally.",
        "Compliance gates prevent any review until final completion.",
    ),
    q(
        "Project Work",
        "A team repeatedly loses time because approvals sit in email threads without clear owners. What is the best response?",
        "Make workflow ownership and approval steps explicit so work can move predictably.",
        "Increase the number of status meetings to compensate for the delay.",
        "Ask the sponsor to approve every item personally.",
        "Remove all approval steps because handoffs create waste.",
    ),
    q(
        "Quality",
        "Defects are being found late because testers are involved only at the end of each release. What should the project manager do?",
        "Integrate quality practices earlier so defects are prevented or detected sooner.",
        "Accept the late defects because final testing is the proper control point.",
        "Reduce testing scope to preserve the schedule baseline.",
        "Move defect ownership entirely to the customer.",
    ),
    q(
        "Uncertainty",
        "A previously identified risk has occurred and is now affecting delivery. How should it be treated?",
        "Manage it as an issue while updating risk information and executing the appropriate response.",
        "Keep it in the risk register only until the next reporting period.",
        "Ignore it because identified risks should not surprise the team.",
        "Close it immediately because it is no longer uncertain.",
    ),
    q(
        "Team",
        "Two senior team members disagree on a solution approach and the rest of the team has stopped contributing. What should the project manager do first?",
        "Facilitate a constructive discussion using agreed decision criteria so the team can converge.",
        "Pick the view of the most senior expert to restore speed.",
        "Escalate the disagreement to procurement.",
        "Split the work into two parallel solutions without further discussion.",
    ),
    q(
        "Stakeholders",
        "A customer representative keeps bypassing the product owner and giving priorities directly to developers. What should the project manager do?",
        "Reinforce the agreed decision path while preserving collaboration with the customer.",
        "Allow the behavior because customer direction always overrides product ownership.",
        "Remove the customer from team ceremonies until trust improves.",
        "Tell developers to decide priorities themselves.",
    ),
    q(
        "Planning",
        "A project's longest path has no float, and one critical activity slips by three days with no recovery action. What is the likely result?",
        "The project completion date is likely to slip by three days.",
        "Only cost will change because float affects budget, not schedule.",
        "Nothing changes because critical path activities are already expected to vary.",
        "The delay automatically becomes a risk instead of a schedule impact.",
    ),
    q(
        "Project Work",
        "A vendor will deliver a key component, but internal teams have not aligned installation dates, testing windows, or acceptance criteria. What should the project manager do first?",
        "Coordinate the dependencies and shared readiness conditions before delivery occurs.",
        "Wait for the component to arrive and resolve details during installation.",
        "Transfer all coordination responsibility to the vendor.",
        "Move acceptance to project closing to reduce short-term pressure.",
    ),
    q(
        "Delivery",
        "A team finishes most stories, but stakeholders say increments are not usable because integration is deferred. What should improve?",
        "The definition of done and delivery workflow so increments are potentially releasable.",
        "The number of stories started each sprint.",
        "The frequency of retrospectives only.",
        "The contract reporting format.",
    ),
    q(
        "Ethics",
        "A team lead asks the project manager to hide a known defect until after user acceptance so the schedule appears on track. What should the project manager do?",
        "Report the issue transparently and manage it according to quality and stakeholder needs.",
        "Hide the defect temporarily because acceptance is the customer's responsibility.",
        "Delay documenting the defect until the next phase to avoid concern.",
        "Remove defect tracking from status reports so the team is not blamed.",
    ),
    q(
        "Measurement",
        "Stakeholders want to know whether recent scope additions are affecting delivery predictability in a hybrid project. Which metric or view is most useful?",
        "A trend showing committed work versus completed work over recent iterations and releases.",
        "The original charter approval date.",
        "The number of team members on vacation.",
        "The procurement audit checklist.",
    ),
]


def build_question(prompt_number: int, topic: str, stem: str, correct: str, distractors: list[str]) -> dict:
    correct_slot = (prompt_number - 1) % 4
    correct_option = OPTION_KEYS[correct_slot]
    distractor_iter = iter(distractors)
    options = []

    for index, key in enumerate(OPTION_KEYS):
        if index == correct_slot:
            text = correct
        else:
            text = next(distractor_iter)
        options.append({"key": key, "text": text})

    return {
        "id": prompt_number,
        "promptNumber": prompt_number,
        "topic": topic,
        "source": BANK_SOURCE,
        "stem": stem,
        "options": options,
        "correctOption": correct_option,
    }


def load_source_bank() -> dict:
    payload = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    for bank in payload.get("banks", []):
        if bank.get("id") == SOURCE_BANK_ID:
            return bank
    raise RuntimeError(f"Source bank '{SOURCE_BANK_ID}' not found in {QUESTIONS_PATH}")


def build_bank() -> dict:
    source_bank = load_source_bank()
    selected_questions = []

    for question in source_bank.get("questions", []):
        if question.get("topic") in EXCLUDED_TOPICS:
            continue

        selected_questions.append(
            {
                "topic": question["topic"],
                "stem": question["stem"],
                "correct": next(option["text"] for option in question["options"] if option["key"] == question["correctOption"]),
                "distractors": [option["text"] for option in question["options"] if option["key"] != question["correctOption"]],
            }
        )

    if len(selected_questions) != 180:
        raise RuntimeError(f"Expected 180 source questions after exclusions, found {len(selected_questions)}")

    if len(SUPPLEMENTAL_BLUEPRINTS) != 20:
        raise RuntimeError(f"Expected 20 supplemental questions, found {len(SUPPLEMENTAL_BLUEPRINTS)}")

    blueprints = selected_questions + [
        {"topic": topic, "stem": stem, "correct": correct, "distractors": distractors}
        for topic, stem, correct, distractors in SUPPLEMENTAL_BLUEPRINTS
    ]

    questions = []
    for prompt_number, item in enumerate(blueprints, start=1):
        questions.append(build_question(prompt_number, item["topic"], item["stem"], item["correct"], item["distractors"]))

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
    print(f"Total questions across all banks: {payload['totalQuestions']}")


if __name__ == "__main__":
    update_questions_json()
