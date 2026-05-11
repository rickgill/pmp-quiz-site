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

let questionBank = [];

function loadQuestionBank() {
  const raw = fs.readFileSync(QUESTIONS_PATH, "utf8");
  const payload = JSON.parse(raw);
  questionBank = Array.isArray(payload.questions) ? payload.questions : [];
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
  const parsed = Number.parseInt(String(value || "20"), 10);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    return 20;
  }
  return Math.min(parsed, 50);
}

function buildBatch(batchNumber, batchSize) {
  const totalQuestions = questionBank.length;
  const totalBatches = Math.ceil(totalQuestions / batchSize);
  const safeBatch = Math.min(Math.max(batchNumber, 1), Math.max(totalBatches, 1));
  const startIndex = (safeBatch - 1) * batchSize;
  const questions = questionBank.slice(startIndex, startIndex + batchSize);

  return {
    batchNumber: safeBatch,
    batchSize,
    totalQuestions,
    totalBatches,
    questions,
  };
}

function scoreBatch(body) {
  const answers = Array.isArray(body.answers) ? body.answers : [];
  const answerMap = new Map(
    answers
      .filter((item) => item && Number.isFinite(item.id) && typeof item.selectedOption === "string")
      .map((item) => [item.id, item.selectedOption.trim().toUpperCase()])
  );

  const results = [];
  let correctCount = 0;

  for (const question of questionBank) {
    if (!answerMap.has(question.id)) {
      continue;
    }

    const selectedOption = answerMap.get(question.id);
    const isCorrect = selectedOption === question.correctOption;
    if (isCorrect) {
      correctCount += 1;
    }

    results.push({
      id: question.id,
      promptNumber: question.promptNumber,
      selectedOption,
      correctOption: question.correctOption,
      correctAnswerText: question.options.find((option) => option.key === question.correctOption)?.text || "",
      isCorrect,
    });
  }

  return {
    attempted: results.length,
    correct: correctCount,
    incorrect: results.length - correctCount,
    scorePct: results.length ? (correctCount / results.length) * 100 : 0,
    results,
  };
}

loadQuestionBank();

const server = http.createServer((req, res) => {
  const requestUrl = new URL(req.url, `http://${req.headers.host}`);

  if (requestUrl.pathname === "/health" && req.method === "GET") {
    sendJson(res, 200, { ok: true, totalQuestions: questionBank.length });
    return;
  }

  if (requestUrl.pathname === "/api/quiz/meta" && req.method === "GET") {
    sendJson(res, 200, {
      totalQuestions: questionBank.length,
      defaultBatchSize: 20,
      totalBatches: Math.ceil(questionBank.length / 20),
      title: "PMP Quiz Trainer",
    });
    return;
  }

  if (requestUrl.pathname === "/api/quiz/batch" && req.method === "GET") {
    const batchSize = normalizeBatchSize(requestUrl.searchParams.get("size"));
    const batchNumber = Number.parseInt(requestUrl.searchParams.get("batch") || "1", 10) || 1;
    sendJson(res, 200, buildBatch(batchNumber, batchSize));
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
        sendJson(res, 200, scoreBatch(body));
      } catch (error) {
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
