const statusEl = document.querySelector("#status");
const metaCopyEl = document.querySelector("#meta-copy");
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

const batchSize = 20;
let quizMeta = null;
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

async function apiRequest(url, options = {}) {
  const response = await fetch(url, options);
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.error || "Request failed.");
  }
  return payload;
}

function updateSummary() {
  const answered = answeredIds.size;
  progressCopyEl.textContent = `${answered} / ${currentBatch?.questions?.length || 0} answered`;
  scoreCopyEl.textContent = `${correctCount} correct`;
  batchCopyEl.textContent = `Batch ${currentBatch?.batchNumber || 1} of ${currentBatch?.totalBatches || 1}`;
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

async function scoreCurrentBatch() {
  const answers = currentBatch.questions.map((question) => ({
    id: question.id,
    selectedOption: selectedAnswers.get(question.id) || "",
  }));
  return apiRequest("/api/quiz/score", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ answers }),
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

function createQuestionCard(question, index) {
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
      selectedAnswers.set(question.id, selectedKey);
      answeredIds.add(question.id);

      if (selectedKey === question.correctOption) {
        correctCount += 1;
        feedbackEl.className = "answer-feedback answer-feedback-correct";
        feedbackEl.textContent = `Correct. ${question.correctOption}: ${
          question.options.find((item) => item.key === question.correctOption)?.text || ""
        }`;
      } else {
        feedbackEl.className = "answer-feedback answer-feedback-incorrect";
        feedbackEl.textContent = `Incorrect. Correct answer: ${question.correctOption}: ${
          question.options.find((item) => item.key === question.correctOption)?.text || ""
        }`;
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

async function loadBatch(batchNumber) {
  loadBatchButton.disabled = true;
  nextBatchButton.disabled = true;
  setStatus(`Loading batch ${batchNumber}...`);

  try {
    currentBatch = await apiRequest(`/api/quiz/batch?batch=${batchNumber}&size=${batchSize}`);
    selectedAnswers = new Map();
    answeredIds = new Set();
    correctCount = 0;
    batchSelectEl.value = String(currentBatch.batchNumber);
    renderBatch();
    setStatus(`Batch ${currentBatch.batchNumber} loaded. Answer each question to see feedback immediately.`);
  } catch (error) {
    setStatus(error.message);
  } finally {
    loadBatchButton.disabled = false;
  }
}

async function loadMeta() {
  setStatus("Loading question bank...");

  try {
    quizMeta = await apiRequest("/api/quiz/meta");
    metaCopyEl.textContent = `${quizMeta.totalQuestions} questions available across ${quizMeta.totalBatches} batches.`;
    batchSelectEl.innerHTML = "";
    for (let index = 1; index <= quizMeta.totalBatches; index += 1) {
      const option = document.createElement("option");
      option.value = String(index);
      option.textContent = `Batch ${index}`;
      batchSelectEl.appendChild(option);
    }
    await loadBatch(1);
  } catch (error) {
    setStatus(error.message);
  }
}

loadBatchButton.addEventListener("click", () => {
  const batchNumber = Number.parseInt(batchSelectEl.value || "1", 10) || 1;
  loadBatch(batchNumber);
});

nextBatchButton.addEventListener("click", () => {
  if (!currentBatch) {
    return;
  }
  const nextBatch = currentBatch.batchNumber + 1;
  if (nextBatch <= currentBatch.totalBatches) {
    loadBatch(nextBatch);
  }
});

loadMeta();
