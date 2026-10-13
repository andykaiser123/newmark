"""AI-backed document analysis; run with uvicorn server:app --host 127.0.0.1 --port 8000."""
import base64
import json
import os
from pathlib import Path
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from openai import OpenAI

app = FastAPI(title='Newmark Multifamily AI Analyzer')
ROOT = Path(__file__).resolve().parent
MAX_BYTES = 20 * 1024 * 1024

PROMPT = '''You are an experienced multifamily investment sales underwriting analyst. Read the ENTIRE attached offering memorandum, particularly Financial Analysis, Underwriting, Rent Roll, Pro Forma, and Financing pages. Do not confuse subject with sales comparables. Distinguish in-place from pro forma and stated facts from assumptions. Extract numbers exactly as printed, preserving source page numbers. Do not fabricate missing data. Return ONLY a JSON object with two properties:
"fields": object keyed by these UI fields when supported: price (asking price $), units (number), sf (building rentable SF, not total unit-mix SF if property details gives building size), currentRent (monthly weighted-average in-place rent per unit), rent (monthly weighted-average market rent per unit), occ (100 minus vacancy percent), exp (pro forma operating expenses divided by pro forma EGI, percent), ltv (loan divided by price percent), rate (annual loan interest percent), amort (years), cap (pro forma cap rate percent). Each entry MUST be {"value": number, "page": integer, "evidence": string, "confidence": "high"|"medium"|"low"}. Only include values with evidence. For currentRent and rent, prefer explicit weighted average totals from unit mix table; use weighted calculations if needed and say so. For exp use expense / EGI if both printed, explain computation. For ltv use the stated financing section. Do not infer renovation budget or growth rates.
"financials": object keyed by currentEGI, proformaEGI, currentExpenses, proformaExpenses, currentNOI, proformaNOI, annualDebtService, loanAmount, monthlyPayment, currentCashFlow, proformaCashFlow. Each entry MUST be {"value": number, "page": integer, "evidence": string}. Omit absent values.
If source numbers conflict, prioritize the detailed underwriting/financial tables and explain the conflict in evidence. Use source PDF page numbers (1-indexed).'''

@app.get('/')
def home():
    return FileResponse(ROOT / 'index.html')

@app.post('/api/analyze')
async def analyze(file: UploadFile = File(...)):
    if not os.getenv('OPENAI_API_KEY'):
        raise HTTPException(503, 'Server missing OPENAI_API_KEY. Configure it on the server, never in the browser.')
    name = file.filename or 'offering-memorandum.pdf'
    if not name.lower().endswith('.pdf'):
        raise HTTPException(400, 'AI analysis currently accepts PDF offering memorandums. XLSX/CSV still work with the existing browser parser.')
    raw = await file.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise HTTPException(413, 'PDF exceeds 20 MB limit.')
    if not raw.startswith(b'%PDF'):
        raise HTTPException(400, 'Invalid PDF file.')
    encoded = base64.b64encode(raw).decode('ascii')
    try:
        client = OpenAI(timeout=120)
        response = client.responses.create(
            model=os.getenv('OPENAI_MODEL', 'gpt-4.1'),
            instructions=PROMPT,
            input=[{'role':'user','content':[
                {'type':'input_text','text':'Analyze this OM carefully and return the specified JSON.'},
                {'type':'input_file','filename':name,'file_data':'data:application/pdf;base64,'+encoded}
            ]}],
            text={'format':{'type':'json_object'}},
        )
        data = json.loads(response.output_text)
        fields = data.get('fields', {})
        financials = data.get('financials', {})
        valid = {'price','units','sf','currentRent','rent','occ','exp','ltv','rate','amort','cap'}
        cleaned = {}
        for key, entry in fields.items():
            if key not in valid or not isinstance(entry, dict):
                continue
            try:
                value = float(entry['value'])
                page = int(entry['page'])
                if not (value > 0 and page > 0):
                    continue
                cleaned[key] = {'value':value,'page':page,'evidence':str(entry.get('evidence',''))[:500], 'confidence':str(entry.get('confidence','medium'))}
            except (ValueError, TypeError, KeyError):
                pass
        return {'fields':cleaned,'financials':financials,'filename':name,'notice':'AI-extracted figures require verification against source OM before client use.'}
    except Exception as exc:
        # Do not expose internal API details or secrets to browser.
        raise HTTPException(502, 'AI analysis failed. Check server logs and model access.') from exc
