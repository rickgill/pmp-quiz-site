# PMP Quiz Site

This project turns the provided PMP PDF question banks into a Railway-ready quiz site.

## Features

- 20-question batches
- immediate inline answer feedback after each selection
- end-of-batch score summary
- batch navigation across the full question bank
- local static frontend with a lightweight Node server

## Run locally

```powershell
node server.js
```

Then open:

```text
http://localhost:3040
```

## Health check

```text
http://localhost:3040/health
```

## Rebuild the question bank

The importer expects text-based PDFs and uses `pypdf`.

```powershell
py scripts/extract_questions.py --input "C:\path\to\file1.pdf" "C:\path\to\file2.pdf" --output data\questions.json
```
