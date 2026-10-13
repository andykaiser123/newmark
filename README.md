# Newmark Multifamily AI Analyzer — prototype

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
export OPENAI_API_KEY='your-key'   # Windows PowerShell: $env:OPENAI_API_KEY='your-key'
uvicorn server:app --host 127.0.0.1 --port 8000
```

Visit http://127.0.0.1:8000. Click **Analyze OM with AI** after selecting a PDF. Review and apply extracted figures.

This is an unhosted prototype. AI requires a backend, paid API access, and an internet connection. Do not put the API key in HTML/JavaScript. Before public deployment add authentication, request quotas, secure upload retention policy, malware scanning, rate limiting, and logging/redaction controls. OMs are sent to the configured AI provider for processing; obtain authorization to upload confidential deal documents. Listing URL fetching is not implemented; upload the PDF instead. Verify financials and derived assumptions before use. No live API test has been run here.
