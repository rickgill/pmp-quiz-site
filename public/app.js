const statusEl = document.querySelector("#status");
const metaCopyEl = document.querySelector("#meta-copy");
const bankTabsEl = document.querySelector("#bank-tabs");
const batchSelectEl = document.querySelector("#batch-select");
const loadBatchButton = document.querySelector("#load-batch-button");
const questionListEl = document.querySelector("#question-list");
const batchSummaryEl = document.querySelector("#batch-summary");
const progressCopyEl = document.querySelector("#progress-copy");
const scoreCopyEl = document.querySelector("#score-copy");
const batchCopyEl = document.querySelector("#batch-copy");
const finalScorePanelEl = document.querySelector("#final-score-panel");
const finalScoreGridEl = document.querySelector("#final-score-grid");
const nextBatchButton = document.querySelector("#next-batch-button");

let quizMeta = null;
let currentBankId = null;
let currentBatch = null;
let selectedAnswers = new Map();
let answeredIds = new Set();
let correctCount = 0;

function setStatus(message) {
  statusEl.textContent = message || "";
}

function formatPercent(value) {
  return `${value.toFixed(0)}%`;
}

function shuffleList(items) {
  const copy = [...items];
  for (let index = copy.length - 1; index > 0; index -= 1) {
    const swapIndex = Math.floor(Math.random() * (index + 1));
    [copy[index], copy[swapIndex]] = [copy[swapIndex], copy[index]];
  }
  return copy;
}

async function apiRequest(url, options = {}) {
  const response = await fetch(url, options);
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.error || "Request failed.");
  }
  return payload;
}

function getCurrentBank() {
  return quizMeta?.banks?.find((bank) => bank.id === currentBankId) || null;
}

function updateSummary() {
  const currentBank = getCurrentBank();
  const answered = answeredIds.size;
  progressCopyEl.textContent = `${answered} / ${currentBatch?.questions?.length || 0} answered`;
  scoreCopyEl.textContent = `${correctCount} correct`;
  batchCopyEl.textContent = `${currentBank?.title || "Question Bank"} • Batch ${currentBatch?.batchNumber || 1} of ${currentBatch?.totalBatches || 1}`;
}

function buildFinalScoreCard(label, value) {
  const article = document.createElement("article");
  article.className = "score-card";
  article.innerHTML = `
    <span class="summary-label">${label}</span>
    <strong>${value}</strong>
  `;
  return article;
}

function buildAnswerPayload(question) {
  const response = selectedAnswers.get(question.id);
  if (!response) {
    return { id: question.id };
  }
  return { id: question.id, ...response };
}

async function scoreCurrentBatch() {
  const answers = currentBatch.questions.map((question) => buildAnswerPayload(question));
  return apiRequest("/api/quiz/score", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ bankId: currentBankId, answers }),
  });
}

async function finalizeBatch() {
  try {
    const score = await scoreCurrentBatch();
    finalScoreGridEl.innerHTML = "";
    finalScoreGridEl.appendChild(buildFinalScoreCard("Correct", String(score.correct)));
    finalScoreGridEl.appendChild(buildFinalScoreCard("Incorrect", String(score.incorrect)));
    finalScoreGridEl.appendChild(buildFinalScoreCard("Attempted", String(score.attempted)));
    finalScoreGridEl.appendChild(buildFinalScoreCard("Score", formatPercent(score.scorePct)));
    finalScorePanelEl.classList.remove("hidden");
    nextBatchButton.disabled = currentBatch.batchNumber >= currentBatch.totalBatches;
    setStatus("Batch complete. Review your score summary or continue to the next batch.");
  } catch (error) {
    setStatus(error.message);
  }
}

function maybeFinalizeBatch() {
  if (!currentBatch || answeredIds.size !== currentBatch.questions.length) {
    return;
  }
  finalizeBatch();
}

function renderMultipleChoiceFeedback(feedbackEl, question, selectedKey) {
  const correctAnswerText = question.options.find((item) => item.key === question.correctOption)?.text || "";
  if (selectedKey === question.correctOption) {
    feedbackEl.className = "answer-feedback answer-feedback-correct";
    feedbackEl.textContent = `Correct. ${question.correctOption}: ${correctAnswerText}`;
    return true;
  }

  feedbackEl.className = "answer-feedback answer-feedback-incorrect";
  feedbackEl.textContent = `Incorrect. Correct answer: ${question.correctOption}: ${correctAnswerText}`;
  return false;
}

function buildMatchSummary(question) {
  const choiceLookup = new Map((question.choices || []).map((item) => [item.id, item.text]));
  const promptLookup = new Map((question.prompts || []).map((item) => [item.id, item.text]));
  return (question.correctMatches || [])
    .map((item) => `${promptLookup.get(item.promptId) || item.promptId} → ${choiceLookup.get(item.choiceId) || item.choiceId}`)
    .join(" | ");
}

function renderDragDropFeedback(feedbackEl, question, isCorrect) {
  if (isCorrect) {
    feedbackEl.className = "answer-feedback answer-feedback-correct";
    feedbackEl.textContent = "Correct. All matches are in the right place.";
    return;
  }

  feedbackEl.className = "answer-feedback answer-feedback-incorrect";
  feedbackEl.textContent = `Incorrect. Correct matches: ${buildMatchSummary(question)}`;
}

function createMultipleChoiceCard(question, index) {
  const article = document.createElement("article");
  article.className = "question-card";
  article.innerHTML = `
    <div class="question-head">
      <div>
        <p class="field-label">Question ${index + 1}</p>
        <h2>#${question.promptNumber}</h2>
      </div>
      <span class="topic-chip">${question.topic || "PMP"}</span>
    </div>
    <p class="question-stem">${question.stem}</p>
    <div class="options-list"></div>
    <div class="answer-feedback hidden"></div>
  `;

  const optionsListEl = article.querySelector(".options-list");
  const feedbackEl = article.querySelector(".answer-feedback");

  function lockQuestion() {
    optionsListEl.querySelectorAll("button").forEach((button) => {
      button.disabled = true;
    });
  }

  function markOptionStyles(selectedKey) {
    optionsListEl.querySelectorAll("button").forEach((button) => {
      const key = button.dataset.key;
      button.classList.toggle("correct", key === question.correctOption);
      button.classList.toggle("incorrect", key === selectedKey && key !== question.correctOption);
    });
  }

  question.options.forEach((option) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "option-button";
    button.dataset.key = option.key;
    button.innerHTML = `
      <span class="option-key">${option.key}</span>
      <span class="option-text">${option.text}</span>
    `;
    button.addEventListener("click", () => {
      if (answeredIds.has(question.id)) {
        return;
      }

      const selectedKey = option.key;
      selectedAnswers.set(question.id, { selectedOption: selectedKey });
      answeredIds.add(question.id);

      const isCorrect = renderMultipleChoiceFeedback(feedbackEl, question, selectedKey);
      if (isCorrect) {
        correctCount += 1;
      }

      feedbackEl.classList.remove("hidden");
      markOptionStyles(selectedKey);
      lockQuestion();
      updateSummary();
      maybeFinalizeBatch();
    });
    optionsListEl.appendChild(button);
  });

  return article;
}

function createChoiceChip(choice, onDragStart) {
  const chip = document.createElement("div");
  chip.className = "drag-choice-chip";
  chip.draggable = true;
  chip.dataset.choiceId = choice.id;
  chip.textContent = choice.text;
  chip.addEventListener("dragstart", (event) => onDragStart(event, choice.id));
  return chip;
}

function createDragDropCard(question, index) {
  const article = document.createElement("article");
  article.className = "question-card";
  article.innerHTML = `
    <div class="question-head">
      <div>
        <p class="field-label">Question ${index + 1}</p>
        <h2>#${question.promptNumber}</h2>
      </div>
      <span class="topic-chip">${question.topic || "Drag & Drop"}</span>
    </div>
    <p class="question-stem">${question.stem}</p>
    <div class="drag-drop-shell">
      <div>
        <p class="field-label">Choices</p>
        <div class="drag-choice-pool" data-pool></div>
      </div>
      <div>
        <p class="field-label">${question.type === "drag-drop-group" ? "Drop Into The Right Group" : "Match Each Prompt"}</p>
        <div class="drag-prompt-list" data-prompt-list></div>
      </div>
    </div>
    <div class="drag-drop-actions">
      <button type="button" class="drag-check-button">Check Answer</button>
      <button type="button" class="drag-reset-button">Reset</button>
    </div>
    <div class="answer-feedback hidden"></div>
  `;

  const poolEl = article.querySelector("[data-pool]");
  const promptListEl = article.querySelector("[data-prompt-list]");
  const checkButton = article.querySelector(".drag-check-button");
  const resetButton = article.querySelector(".drag-reset-button");
  const feedbackEl = article.querySelector(".answer-feedback");

  const choices = shuffleList(question.choices || []);
  const promptLookup = new Map((question.prompts || []).map((item) => [item.id, item]));
  const choiceLookup = new Map((question.choices || []).map((item) => [item.id, item]));
  const assignments = new Map();

  (question.choices || []).forEach((choice) => {
    assignments.set(choice.id, null);
  });

  function onDragStart(event, choiceId) {
    if (answeredIds.has(question.id)) {
      event.preventDefault();
      return;
    }
    event.dataTransfer.setData("text/plain", choiceId);
  }

  function setDropTargetHandlers(targetEl, promptId) {
    targetEl.addEventListener("dragover", (event) => {
      if (!answeredIds.has(question.id)) {
        event.preventDefault();
      }
    });
    targetEl.addEventListener("drop", (event) => {
      if (answeredIds.has(question.id)) {
        return;
      }
      event.preventDefault();
      const choiceId = event.dataTransfer.getData("text/plain");
      if (!choiceId || !assignments.has(choiceId)) {
        return;
      }

      if (promptId && question.type === "drag-drop") {
        assignments.forEach((value, key) => {
          if (value === promptId) {
            assignments.set(key, null);
          }
        });
      }

      assignments.set(choiceId, promptId || null);
      renderState();
    });
  }

  function buildSelectedPairs() {
    const pairs = [];
    assignments.forEach((promptId, choiceId) => {
      if (promptId) {
        pairs.push({ promptId, choiceId });
      }
    });
    return pairs;
  }

  function isComplete() {
    if (question.type === "drag-drop-group") {
      return [...assignments.values()].every((value) => Boolean(value));
    }
    return (question.prompts || []).every((prompt) => [...assignments.values()].includes(prompt.id));
  }

  function renderState() {
    poolEl.innerHTML = "";
    promptListEl.innerHTML = "";

    choices.forEach((choice) => {
      if (!assignments.get(choice.id)) {
        poolEl.appendChild(createChoiceChip(choice, onDragStart));
      }
    });

    (question.prompts || []).forEach((prompt) => {
      const promptCard = document.createElement("div");
      promptCard.className = "drag-prompt-card";
      promptCard.innerHTML = `
        <div class="drag-prompt-text">${prompt.text}</div>
        <div class="drag-drop-zone" data-zone="${prompt.id}"></div>
      `;

      const zoneEl = promptCard.querySelector("[data-zone]");
      setDropTargetHandlers(zoneEl, prompt.id);

      [...assignments.entries()]
        .filter(([, assignedPromptId]) => assignedPromptId === prompt.id)
        .forEach(([choiceId]) => {
          zoneEl.appendChild(createChoiceChip(choiceLookup.get(choiceId), onDragStart));
        });

      promptListEl.appendChild(promptCard);
    });

    setDropTargetHandlers(poolEl, null);
    checkButton.disabled = !isComplete() || answeredIds.has(question.id);
    resetButton.disabled = answeredIds.has(question.id);
  }

  checkButton.addEventListener("click", () => {
    if (answeredIds.has(question.id) || !isComplete()) {
      return;
    }

    const selectedPairs = buildSelectedPairs();
    const expected = new Set((question.correctMatches || []).map((item) => `${item.promptId}:${item.choiceId}`));
    const actual = new Set(selectedPairs.map((item) => `${item.promptId}:${item.choiceId}`));
    const isCorrect = expected.size === actual.size && [...expected].every((item) => actual.has(item));

    selectedAnswers.set(question.id, { selectedPairs });
    answeredIds.add(question.id);
    if (isCorrect) {
      correctCount += 1;
    }

    renderDragDropFeedback(feedbackEl, question, isCorrect);
    feedbackEl.classList.remove("hidden");
    renderState();
    updateSummary();
    maybeFinalizeBatch();
  });

  resetButton.addEventListener("click", () => {
    if (answeredIds.has(question.id)) {
      return;
    }
    assignments.forEach((_, choiceId) => assignments.set(choiceId, null));
    renderState();
  });

  renderState();
  return article;
}

function createQuestionCard(question, index) {
  if (question.type === "drag-drop" || question.type === "drag-drop-group") {
    return createDragDropCard(question, index);
  }
  return createMultipleChoiceCard(question, index);
}

function renderBatch() {
  questionListEl.innerHTML = "";
  finalScorePanelEl.classList.add("hidden");
  finalScoreGridEl.innerHTML = "";

  currentBatch.questions.forEach((question, index) => {
    questionListEl.appendChild(createQuestionCard(question, index));
  });

  batchSummaryEl.classList.remove("hidden");
  updateSummary();
}

function renderBankTabs() {
  bankTabsEl.innerHTML = "";
  quizMeta.banks.forEach((bank) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "bank-tab-button";
    button.dataset.bankId = bank.id;
    button.textContent = bank.title;
    button.setAttribute("aria-pressed", String(bank.id === currentBankId));
    if (bank.id === currentBankId) {
      button.classList.add("active");
    }
    button.addEventListener("click", () => {
      if (bank.id === currentBankId) {
        return;
      }
      loadBank(bank.id);
    });
    bankTabsEl.appendChild(button);
  });
}

function populateBatchSelect(bank) {
  batchSelectEl.innerHTML = "";
  for (let index = 1; index <= bank.totalBatches; index += 1) {
    const option = document.createElement("option");
    option.value = String(index);
    option.textContent = `Batch ${index}`;
    batchSelectEl.appendChild(option);
  }
}

async function loadBatch(bankId, batchNumber) {
  loadBatchButton.disabled = true;
  nextBatchButton.disabled = true;
  setStatus(`Loading batch ${batchNumber}...`);

  try {
    currentBatch = await apiRequest(`/api/quiz/batch?bank=${encodeURIComponent(bankId)}&batch=${batchNumber}`);
    currentBankId = currentBatch.bankId;
    selectedAnswers = new Map();
    answeredIds = new Set();
    correctCount = 0;
    batchSelectEl.value = String(currentBatch.batchNumber);
    renderBankTabs();
    renderBatch();
    setStatus(`Loaded ${currentBatch.bankTitle}. Answer each question to see immediate feedback.`);
  } catch (error) {
    setStatus(error.message);
  } finally {
    loadBatchButton.disabled = false;
  }
}

async function loadBank(bankId) {
  const bank = quizMeta?.banks?.find((item) => item.id === bankId);
  if (!bank) {
    return;
  }
  currentBankId = bank.id;
  populateBatchSelect(bank);
  await loadBatch(bank.id, 1);
}

async function loadMeta() {
  setStatus("Loading question banks...");

  try {
    quizMeta = await apiRequest("/api/quiz/meta");
    currentBankId = quizMeta.defaultBankId;
    renderBankTabs();
    const defaultBank = getCurrentBank();
    if (!defaultBank) {
      throw new Error("No question banks are available.");
    }
    metaCopyEl.textContent = `${quizMeta.totalQuestions} questions across ${quizMeta.banks.length} tabs.`;
    populateBatchSelect(defaultBank);
    await loadBatch(defaultBank.id, 1);
  } catch (error) {
    setStatus(error.message);
  }
}

loadBatchButton.addEventListener("click", () => {
  const batchNumber = Number.parseInt(batchSelectEl.value || "1", 10) || 1;
  loadBatch(currentBankId, batchNumber);
});

nextBatchButton.addEventListener("click", () => {
  if (!currentBatch) {
    return;
  }
  const nextBatch = currentBatch.batchNumber + 1;
  if (nextBatch <= currentBatch.totalBatches) {
    loadBatch(currentBankId, nextBatch);
  }
});

loadMeta();
