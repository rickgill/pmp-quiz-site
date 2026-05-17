const http = require("http");
const fs = require("fs");
const path = require("path");

const PORT = process.env.PORT || 3040;
const PUBLIC_DIR = path.join(__dirname, "public");
const DATA_DIR = path.join(__dirname, "data");
const QUESTIONS_PATH = path.join(DATA_DIR, "questions.json");

const MIME_TYPES = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "application/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
};

const STATIC_ROUTE_ALIASES = {
  "/": "/index.html",
};

let quizData = {
  title: "PMP Quiz Trainer",
  batchSize: 20,
  totalQuestions: 0,
  banks: [],
};

function slugify(value) {
  return String(value || "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "") || "bank";
}

function normalizeSourceLabel(value, fallback) {
  const normalized = String(value || "").replace(/â€“/g, "-").trim();
  return normalized || fallback;
}

function buildLegacyBank(payload) {
  const questions = Array.isArray(payload.questions) ? payload.questions : [];
  const firstSource = normalizeSourceLabel(questions[0]?.source, "Original Bank");
  const bankId = slugify(firstSource);
  return {
    id: bankId,
    title: firstSource.replace(/\.pdf$/i, ""),
    source: firstSource,
    totalQuestions: questions.length,
    questions,
  };
}

function normalizeBank(bank, fallbackIndex) {
  const questions = Array.isArray(bank.questions) ? bank.questions : [];
  const source = normalizeSourceLabel(bank.source || bank.title, `Bank ${fallbackIndex + 1}`);
  return {
    id: slugify(bank.id || source),
    title: String(bank.title || source).replace(/\.pdf$/i, ""),
    source,
    totalQuestions: questions.length,
    questions,
  };
}

function loadQuestionBank() {
  const raw = fs.readFileSync(QUESTIONS_PATH, "utf8");
  const payload = JSON.parse(raw);
  const banks = Array.isArray(payload.banks) && payload.banks.length
    ? payload.banks.map((bank, index) => normalizeBank(bank, index))
    : [buildLegacyBank(payload)];

  quizData = {
    title: payload.title || "PMP Quiz Trainer",
    batchSize: Number.parseInt(String(payload.batchSize || "20"), 10) || 20,
    totalQuestions: banks.reduce((sum, bank) => sum + bank.totalQuestions, 0),
    banks,
  };
}

function sendJson(res, statusCode, payload) {
  res.writeHead(statusCode, {
    "Content-Type": "application/json; charset=utf-8",
    "Cache-Control": "no-cache",
  });
  res.end(JSON.stringify(payload));
}

function serveStatic(reqPath, res) {
  const relativePath = STATIC_ROUTE_ALIASES[reqPath] || reqPath;
  const normalizedPath = path.normalize(relativePath).replace(/^(\.\.[/\\])+/, "");
  const filePath = path.join(PUBLIC_DIR, normalizedPath);

  if (!filePath.startsWith(PUBLIC_DIR)) {
    sendJson(res, 403, { error: "Forbidden" });
    return;
  }

  fs.readFile(filePath, (error, content) => {
    if (error) {
      if (error.code === "ENOENT") {
        sendJson(res, 404, { error: "Not found" });
        return;
      }
      sendJson(res, 500, { error: "Failed to read file." });
      return;
    }

    const ext = path.extname(filePath).toLowerCase();
    res.writeHead(200, {
      "Content-Type": MIME_TYPES[ext] || "application/octet-stream",
      "Cache-Control": "no-cache",
    });
    res.end(content);
  });
}

function normalizeBatchSize(value) {
  const parsed = Number.parseInt(String(value || quizData.batchSize || "20"), 10);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    return quizData.batchSize || 20;
  }
  return Math.min(parsed, 50);
}

function findBankById(bankId) {
  const fallbackBank = quizData.banks[0] || null;
  if (!bankId) {
    return fallbackBank;
  }
  return quizData.banks.find((bank) => bank.id === bankId) || fallbackBank;
}

function buildBatch(bank, batchNumber, batchSize) {
  const totalQuestions = bank.questions.length;
  const totalBatches = Math.ceil(totalQuestions / batchSize);
  const safeBatch = Math.min(Math.max(batchNumber, 1), Math.max(totalBatches, 1));
  const startIndex = (safeBatch - 1) * batchSize;
  const questions = bank.questions.slice(startIndex, startIndex + batchSize);

  return {
    bankId: bank.id,
    bankTitle: bank.title,
    batchNumber: safeBatch,
    batchSize,
    totalQuestions,
    totalBatches,
    questions,
  };
}

function scoreBatch(body) {
  const bank = findBankById(body.bankId);
  if (!bank) {
    return { statusCode: 404, payload: { error: "Question bank not found." } };
  }

  const answers = Array.isArray(body.answers) ? body.answers : [];
  const answerMap = new Map(answers.filter((item) => item && Number.isFinite(item.id)).map((item) => [item.id, item]));

  const results = [];
  let correctCount = 0;

  for (const question of bank.questions) {
    if (!answerMap.has(question.id)) {
      continue;
    }

    const response = answerMap.get(question.id);
    let isCorrect = false;

    if (question.type === "drag-drop" || question.type === "drag-drop-group") {
      const expected = new Set(
        (Array.isArray(question.correctMatches) ? question.correctMatches : []).map(
          (item) => `${item.promptId}:${item.choiceId}`
        )
      );
      const actual = new Set(
        (Array.isArray(response?.selectedPairs) ? response.selectedPairs : []).map(
          (item) => `${item.promptId}:${item.choiceId}`
        )
      );
      isCorrect = expected.size === actual.size && [...expected].every((item) => actual.has(item));
    } else {
      const selectedOption = typeof response?.selectedOption === "string" ? response.selectedOption.trim().toUpperCase() : "";
      isCorrect = selectedOption === question.correctOption;
    }

    if (isCorrect) {
      correctCount += 1;
    }

    if (question.type === "drag-drop" || question.type === "drag-drop-group") {
      results.push({
        id: question.id,
        promptNumber: question.promptNumber,
        type: question.type,
        selectedPairs: Array.isArray(response?.selectedPairs) ? response.selectedPairs : [],
        correctMatches: Array.isArray(question.correctMatches) ? question.correctMatches : [],
        isCorrect,
      });
    } else {
      const selectedOption = typeof response?.selectedOption === "string" ? response.selectedOption.trim().toUpperCase() : "";
      results.push({
        id: question.id,
        promptNumber: question.promptNumber,
        selectedOption,
        correctOption: question.correctOption,
        correctAnswerText: question.options.find((option) => option.key === question.correctOption)?.text || "",
        isCorrect,
      });
    }
  }

  return {
    statusCode: 200,
    payload: {
      attempted: results.length,
      correct: correctCount,
      incorrect: results.length - correctCount,
      scorePct: results.length ? (correctCount / results.length) * 100 : 0,
      results,
    },
  };
}

loadQuestionBank();

const server = http.createServer((req, res) => {
  const requestUrl = new URL(req.url, `http://${req.headers.host}`);

  if (requestUrl.pathname === "/health" && req.method === "GET") {
    sendJson(res, 200, {
      ok: true,
      port: Number(PORT),
      totalQuestions: quizData.totalQuestions,
      totalBanks: quizData.banks.length,
    });
    return;
  }

  if (requestUrl.pathname === "/api/quiz/meta" && req.method === "GET") {
    sendJson(res, 200, {
      title: quizData.title,
      totalQuestions: quizData.totalQuestions,
      defaultBatchSize: quizData.batchSize,
      defaultBankId: quizData.banks[0]?.id || null,
      banks: quizData.banks.map((bank) => ({
        id: bank.id,
        title: bank.title,
        source: bank.source,
        totalQuestions: bank.totalQuestions,
        totalBatches: Math.ceil(bank.totalQuestions / quizData.batchSize),
      })),
    });
    return;
  }

  if (requestUrl.pathname === "/api/quiz/batch" && req.method === "GET") {
    const bank = findBankById(requestUrl.searchParams.get("bank"));
    if (!bank) {
      sendJson(res, 404, { error: "Question bank not found." });
      return;
    }

    const batchSize = normalizeBatchSize(requestUrl.searchParams.get("size"));
    const batchNumber = Number.parseInt(requestUrl.searchParams.get("batch") || "1", 10) || 1;
    sendJson(res, 200, buildBatch(bank, batchNumber, batchSize));
    return;
  }

  if (requestUrl.pathname === "/api/quiz/score" && req.method === "POST") {
    let raw = "";
    req.on("data", (chunk) => {
      raw += chunk;
      if (raw.length > 1_000_000) {
        req.destroy();
      }
    });
    req.on("end", () => {
      try {
        const body = raw ? JSON.parse(raw) : {};
        const { statusCode, payload } = scoreBatch(body);
        sendJson(res, statusCode, payload);
      } catch {
        sendJson(res, 400, { error: "Invalid request body." });
      }
    });
    return;
  }

  if (req.method === "GET") {
    serveStatic(requestUrl.pathname, res);
    return;
  }

  sendJson(res, 404, { error: "Not found" });
});

server.listen(PORT, () => {
  console.log(`PMP quiz site running at http://localhost:${PORT}`);
});
