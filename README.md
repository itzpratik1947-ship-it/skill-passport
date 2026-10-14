# Skill Passport · Code Apex prototype

**One verified, portable identity for everything you can actually do.** This is a Streamlit prototype aligned to the Round 1 presentation: candidate profile, evidence extraction, optional Groq analysis, GitHub project import, adaptive skill quiz and task prompts, per-skill 0–100 assessment scores, role-gap analysis, a 30-day learning plan, privacy-filtered exports, public read-only Passport pages and QR links.

## Feature map

| PPT feature | Prototype implementation | Honest limitation |
|---|---|---|
| Candidate profile / skill entry | Session profile + manually added skill claims | No production login, identity proof, or account recovery |
| Resume/document processing | PDF selectable text, TXT, Markdown | Scanned PDFs need manual text entry; no OCR |
| GitHub project import | Public repository archive ingestion | Public code does not prove candidate authorship |
| Evidence-backed skill profile | Rule-based and optional Groq extraction with source quotations | Evidence status is conservative; claims are not certification |
| AI skill assessment | Optional Groq-generated adaptive quiz; built-in offline question bank | Prototype quiz, not proctored or accredited |
| Practical task prompts | Skill-specific task prompt + optional candidate response | Response is not independently graded in this prototype |
| Common 0–100 score | Score for each completed multiple-choice assessment | Quiz score only; not a formal proficiency certification |
| Role matching / gaps | Requirement extraction and evidence-coverage estimate | Transparent heuristic, not a hiring prediction |
| Learning plan | Prioritized 30-day plan | Generic actions require learner judgment |
| Public link and QR | Random token, public read-only query route, QR PNG; Supabase managed storage supported when configured | SQLite fallback is demo-only; managed database credentials must be configured for durable hosting |
| Privacy controls | Choose visible skills, name/headline, evidence, source links before publishing/export | Anyone with a public link can copy the information; revocation cannot delete copies already made |
| HTML / Markdown / JSON export | Filtered downloadable exports | Downloaded files are outside app access control |
| College/issuer verification | Trust model reserves `Verified` for independent issuer verification | Issuer integrations are future scope and not implemented |
| Recruiter search dashboard / native wallet | Not included | Explicitly beyond hackathon scope in the PPT |

## Windows setup (PowerShell)

From the extracted `Skill-Passport` folder:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Open `.env` and optionally set `GROQ_API_KEY`. Never commit `.env`. Without a Groq key, local evidence extraction and built-in assessment questions still work.

Run:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

If PowerShell blocks environment activation, the direct interpreter command above avoids activation entirely.

## Deploy and enable public Passport links

1. Push this folder to a GitHub repository without `.env`, database files, resumes, or private evidence.
2. Deploy `app.py` on Streamlit Community Cloud.
3. In Streamlit app settings, set `PUBLIC_APP_URL` to the deployed app URL, e.g. `https://your-app-name.streamlit.app`.
4. If using Groq, set `GROQ_API_KEY` and optionally `GROQ_MODEL` in Streamlit Secrets/environment variables.
5. For durable Passport links, create a Supabase project, run `supabase_schema.sql` in its SQL Editor, and set `SUPABASE_URL` plus `SUPABASE_SERVICE_ROLE_KEY` as server-side secrets. Never expose the service-role key to browser/client code. If these are absent, the app falls back to local SQLite.
6. Set `PUBLIC_APP_URL` to the deployed Streamlit URL.
7. Test publishing and open the generated URL in a private/incognito window and on another device; then test revocation.

**Storage warning:** SQLite is a demo fallback. Some hosted app filesystems are ephemeral and multiple replicas do not share local SQLite. Supabase support is included for persistent snapshots, but it is not active until you create/configure the database and verify it in your account. Configure backups, retention and access controls before production use.

## End-to-end demo checklist

1. Enter candidate name and headline.
2. Add a skill such as Python, upload a resume/project text file, and/or import a public GitHub repository.
3. Build/refresh the Passport and inspect every evidence quotation and status.
4. Open **AI skill assessment**, generate a quiz, answer it and submit. Confirm a 0–100 score appears on that skill.
5. Review the practical task prompt and optionally record a short response or project link.
6. Open **Evidence ledger** and verify source names, quotes, evidence types and attribution labels.
7. Enter a target role and job description in the sidebar; run **Analyze target role** and create a 30-day plan.
8. Open **Public Passport & QR**, choose exactly what to share, publish the snapshot, download the QR and open the URL in an incognito browser.
9. Revoke the link and verify it no longer opens.
10. Download HTML, Markdown and JSON exports and confirm privacy settings are respected.
11. Repeat on a phone viewport.

## Trust model

- `Unverified` / self-reported means a learner claim has not been independently checked.
- `Partially supported` means source material supports a signal but does not establish all aspects of proficiency or authorship.
- `Assessment completed · prototype` means the learner completed this app's quiz. The numeric score is stored per skill and is not an accredited credential.
- The formal `Verified` status must not be assigned just because AI suggested it, a resume mentioned it, or a candidate checked an ownership box. Independent issuer verification is not yet integrated.
- A public Passport link verifies the published snapshot in this prototype, not the person's real-world identity or all claims on the page.

## Automated tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

The test suite checks evidence extraction, quote validation, privacy filtering, conservative verification, quiz scoring, and public snapshot storage/revocation. Passing tests are not a substitute for the end-to-end demo checklist above.

## Project structure

```text
Skill-Passport/
├── app.py
├── requirements.txt
├── .env.example
├── README.md
├── supabase_schema.sql
├── demo_data/
│   ├── sample_resume.txt
│   ├── sample_project.md
│   └── sample_job_description.txt
├── connectors/
│   ├── documents.py
│   └── github.py
├── services/
│   ├── ai_client.py
│   ├── assessment.py
│   ├── evidence_extractor.py
│   ├── exporter.py
│   ├── learning_planner.py
│   ├── passport_builder.py
│   ├── passport_store.py
│   ├── privacy.py
│   └── role_matcher.py
└── tests/
```


## OCR for scanned PDFs (Windows)

Skill Passport first extracts selectable text from normal PDFs. For scanned/image-only
PDFs, it can now use OCR through Tesseract.

1. Install the Python dependencies in the project terminal:
   `\.venv\Scripts\python.exe -m pip install -r requirements.txt`
2. Install the **Tesseract OCR application for Windows** (the Python package alone is not
   the OCR engine). Ensure English language data is included.
3. Restart the Streamlit app after installation.
4. Upload the scanned PDF again. OCR-extracted text is marked as OCR and should be
   checked for recognition errors before being used as evidence.
5. If Tesseract is installed but not found, add this line to `.env` using your actual path:
   `TESSERACT_CMD=C:\\Program Files\\Tesseract-OCR\\tesseract.exe`

OCR does not independently verify a certificate. It only reads text from the image.
