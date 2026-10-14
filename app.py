import io
import json
import os
from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit

import qrcode
import streamlit as st

from connectors.documents import extract_uploaded_document
from connectors.github import fetch_github_repository
from services.evidence_extractor import extract_rule_based_evidence
from services.passport_builder import build_passport
from services.role_matcher import analyze_role
from services.learning_planner import create_learning_plan
from services.ai_client import analyze_with_ai, ai_is_configured
from services.assessment import generate_quiz, grade_quiz
from services.exporter import passport_markdown, passport_html
from services.privacy import build_shareable_passport
from services.passport_store import publish_passport, get_public_passport, make_public_url, revoke_passport

st.set_page_config(page_title="Skill Passport", page_icon="🪪", layout="wide", initial_sidebar_state="expanded")


def base_app_url():
    configured = os.getenv("PUBLIC_APP_URL", "").strip().rstrip("/")
    if configured:
        return configured
    try:
        current = st.context.url
        parts = urlsplit(current)
        if parts.hostname in {"localhost", "127.0.0.1", "0.0.0.0"}:
            return ""
        return urlunsplit((parts.scheme, parts.netloc, parts.path, "", "")).rstrip("/")
    except Exception:
        return ""


def qr_png(url):
    qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=8, border=3)
    qr.add_data(url)
    qr.make(fit=True)
    image = qr.make_image(fill_color="#111827", back_color="white")
    out = io.BytesIO()
    image.save(out, format="PNG")
    return out.getvalue()


def show_public_passport(token):
    public = get_public_passport(token)
    st.title("🪪 Skill Passport · Public verification")
    if not public:
        st.error("This Passport link is invalid, expired, or has been revoked.")
        st.caption("A verification page only displays the public snapshot saved by its owner.")
        st.stop()
    candidate = public.get("candidate", {})
    st.subheader(candidate.get("name") or "Anonymous candidate")
    if candidate.get("headline"):
        st.write(candidate["headline"])
    st.caption(f"Passport ID: {public.get('passport_id', 'Not available')} · Snapshot generated: {public.get('created_at', 'unknown')}")
    st.info("This page verifies that the displayed snapshot was published by this prototype. It does not independently certify identity, project authorship, or skill proficiency.")
    for skill in public.get("skills", []):
        with st.container(border=True):
            st.markdown(f"### {skill.get('skill', 'Skill')}")
            score = skill.get("assessment_score")
            if score is not None:
                st.metric("Assessment score", f"{score}/100")
                st.caption(skill.get("assessment_level", "Assessment completed · prototype"))
            st.write(f"**Evidence status:** {skill.get('status', 'Unverified')}")
            st.write(skill.get("summary", ""))
            for ev in skill.get("evidence", []):
                st.caption(f"{ev.get('evidence_type', 'Evidence')} · {ev.get('source_name', 'Source')}")
                if ev.get("quote"):
                    st.code(ev["quote"], language="text")
    st.subheader("Verification notes")
    for note in public.get("notes", []):
        st.write(f"• {note}")
    st.caption("Skill Passport prototype · public read-only snapshot")
    st.stop()


# Public URL mode is intentionally read-only and only serves the filtered published snapshot.
try:
    public_token = st.query_params.get("passport", "")
except Exception:
    public_token = ""
if public_token:
    show_public_passport(public_token)

st.title("🪪 Skill Passport")
st.caption("One evidence-backed, portable profile for what a learner can demonstrate.")
st.markdown("**Learn / Build → Assess → Verify evidence → Passport → Share**")
st.info("Trust labels are deliberately conservative: resume claims, AI output and repository presence are not independent certification. Assessment scores reflect this prototype's quiz, not an accredited exam.")

for key, default in [("passport_result", None), ("source_records", []), ("role_result", None), ("learning_plan", None), ("assessment_questions", None), ("assessment_skill", ""), ("assessment_origin", ""), ("published_token", ""), ("published_url", "")]:
    if key not in st.session_state:
        st.session_state[key] = default

with st.sidebar:
    st.header("1 · Candidate profile")
    candidate_name = st.text_input("Name", placeholder="Your name", key="candidate_name")
    headline = st.text_input("Professional headline", placeholder="Student · Python developer", key="headline")
    st.caption("This prototype keeps the profile in the current app session. It does not implement production account authentication.")
    st.divider()
    st.header("2 · Add evidence")
    manual_skills_text = st.text_input("Skills to assess / add", placeholder="Python, SQL, Git", help="Comma-separated. These start as self-reported claims until supported by evidence or assessment.")
    repo_url = st.text_input("Public GitHub repository URL", placeholder="https://github.com/owner/repository", key="repo_url")
    resume_file = st.file_uploader("Resume (PDF, TXT or MD)", type=["pdf", "txt", "md"], key="resume")
    project_files = st.file_uploader("Project documents / certificates (PDF, TXT or MD)", type=["pdf", "txt", "md"], accept_multiple_files=True, key="projects", help="PDFs must contain selectable text. OCR is disabled; use manual text for scanned documents.")
    manual_document_text = st.text_area("Manual certificate / project details", height=100, placeholder="Course/provider/date, project summary, skills covered…", help="Manually entered details are self-reported, not issuer-verified.")
    repo_is_mine = st.checkbox("I confirm I can explain my contribution to this repository", value=False)
    st.caption("Self-attestation does not independently prove authorship.")
    st.divider()
    st.header("3 · Target role")
    role_name = st.text_input("Target role", placeholder="Junior AI Engineer", key="role_name")
    job_description = st.text_area("Job description / requirements", height=110, placeholder="Paste role requirements…", key="job_description")
    run_button = st.button("Build / refresh Passport", type="primary", use_container_width=True)
    st.divider()
    st.header("AI configuration")
    st.write("Groq is optional. Without a key, the project uses local rules and built-in assessment questions.")
    st.caption("Configure GROQ_API_KEY in .env or Streamlit Secrets. Never commit secrets.")

if run_button:
    source_records, errors = [], []
    if resume_file:
        try:
            source_records.append({"source_id": "resume", "source_type": "resume", "source_name": resume_file.name, "url": "", "owner_confirmed": False, "content": extract_uploaded_document(resume_file)})
        except Exception as exc:
            errors.append(f"Resume: {exc}")
    for idx, upload in enumerate(project_files or []):
        try:
            source_records.append({"source_id": f"document_{idx+1}", "source_type": "project_document", "source_name": upload.name, "url": "", "owner_confirmed": False, "content": extract_uploaded_document(upload)})
        except Exception as exc:
            errors.append(f"{upload.name}: {exc}")
    if manual_document_text.strip():
        source_records.append({"source_id": "manual_document_details", "source_type": "manual_document", "source_name": "Manually entered certificate/project details", "url": "", "owner_confirmed": False, "content": manual_document_text.strip()[:80000]})
    if repo_url.strip():
        try:
            repo = fetch_github_repository(repo_url.strip())
            content = "\n\n".join(f"### FILE: {path}\n{text}" for path, text in repo["files"].items())
            source_records.append({"source_id": "github_repository", "source_type": "github_repository", "source_name": f'{repo["owner"]}/{repo["repo"]}', "url": repo_url.strip(), "owner_confirmed": bool(repo_is_mine), "content": content, "repository": repo})
        except Exception as exc:
            errors.append(f"GitHub repository: {exc}")
    manual_skills = [x.strip() for x in manual_skills_text.split(",") if x.strip()]
    if not source_records and not manual_skills:
        st.error("Add at least one document, public GitHub repository, manual detail, or skill claim.")
    else:
        for error in errors:
            st.warning(error)
        with st.spinner("Extracting evidence and building the profile…"):
            rule_evidence = [ev for source in source_records for ev in extract_rule_based_evidence(source)]
            try:
                ai_result = analyze_with_ai(source_records, role_name.strip(), job_description.strip()) if source_records else None
                ai_error = None
            except Exception as exc:
                ai_result, ai_error = None, str(exc)
            passport = build_passport(candidate={"name": candidate_name.strip(), "headline": headline.strip()}, sources=source_records, rule_evidence=rule_evidence, ai_result=ai_result)
            existing = {x["skill"].casefold() for x in passport.get("skills", [])}
            for skill in manual_skills:
                if skill.casefold() not in existing:
                    passport["skills"].append({"skill": skill, "level": "Not assessed", "status": "Unverified", "confidence": 0.2,
                        "summary": "Self-reported skill claim. No independent evidence has yet been attached.", "evidence": [{"source_name": "Candidate-entered skill", "source": "Candidate-entered skill", "location": "Profile", "quote": skill, "explanation": "This is a self-reported claim, not proof of proficiency.", "evidence_type": "self_reported_claim", "strength": "weak", "attribution_status": "candidate_self_report"}],
                        "limitations": ["Self-reported claim only; complete an assessment and attach relevant project evidence."]})
            passport["skills"].sort(key=lambda x: x["skill"].lower())
            passport["created_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            passport["passport_id"] = "SP-" + datetime.now(timezone.utc).strftime("%Y%m%d") + "-" + os.urandom(3).hex().upper()
            st.session_state.passport_result = passport
            st.session_state.source_records = source_records
            st.session_state.role_result = None
            st.session_state.learning_plan = None
            st.session_state.ai_error = ai_error
            st.session_state.last_target_role = role_name.strip()
            st.session_state.last_job_description = job_description.strip()
            st.session_state.assessment_questions = None
            st.session_state.published_token = ""
            st.session_state.published_url = ""
            st.success("Passport built. Review evidence and complete assessments before sharing.")

passport = st.session_state.passport_result
if passport:
    tabs = st.tabs(["Passport overview", "AI skill assessment", "Evidence ledger", "Role gaps & learning plan", "Public Passport & QR", "Recruiter preview & exports"])
    with tabs[0]:
        candidate = passport.get("candidate", {})
        st.subheader(candidate.get("name") or "Candidate Skill Passport")
        if candidate.get("headline"): st.write(candidate["headline"])
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Skills", len(passport.get("skills", [])))
        c2.metric("Evidence items", sum(len(s.get("evidence", [])) for s in passport.get("skills", [])))
        c3.metric("Sources", len(passport.get("sources", [])))
        c4.metric("Assessed skills", sum(1 for s in passport.get("skills", []) if s.get("assessment_score") is not None))
        st.caption(f"Passport ID: {passport.get('passport_id')} · Generated: {passport.get('created_at')}")
        st.subheader("Skill profile")
        if not passport.get("skills"): st.warning("No skills detected. Add skills manually or upload a more descriptive source.")
        for skill in passport.get("skills", []):
            with st.container(border=True):
                left, right = st.columns([3, 1])
                left.markdown(f"**{skill['skill']}**")
                left.write(skill.get("summary", ""))
                proof_types = sorted({str(ev.get("evidence_type", "evidence")).replace("_", " ") for ev in skill.get("evidence", [])})
                if proof_types:
                    left.caption("Proof type: " + ", ".join(proof_types))
                right.write(f"**Trust status:** {skill.get('status', 'Unverified')}")
                if skill.get("assessment_score") is not None:
                    right.metric("Quiz score", f"{skill['assessment_score']}/100")
                    right.caption(skill.get("assessment_level", "Assessment completed"))
                if skill.get("limitations"):
                    st.caption("Limitations: " + " ".join(skill["limitations"]))
        st.subheader("System notes")
        for note in passport.get("notes", []): st.write(f"• {note}")
        if st.session_state.get("ai_error"): st.warning("Groq analysis failed; local rules were used where possible. " + st.session_state.ai_error)
        elif not ai_is_configured(): st.info("Groq is not configured. Built-in assessment and rule-based extraction remain available.")

    with tabs[1]:
        st.subheader("Adaptive skill assessment")
        st.write("Take a short quiz and receive a skill-specific practical task. Questions adapt to the previous score when Groq is configured; a built-in question bank works offline.")
        skill_names = [s["skill"] for s in passport.get("skills", [])]
        if skill_names:
            selected = st.selectbox("Skill to assess", skill_names, key="assessment_skill_select")
            target_skill = next(s for s in passport["skills"] if s["skill"] == selected)
            previous_score = target_skill.get("assessment_score")
            if previous_score is not None: st.caption(f"Previous attempt: {previous_score}/100. The next attempt will target a suitable difficulty.")
            if st.button("Generate assessment", type="primary", key="generate_quiz"):
                questions, origin = generate_quiz(selected, previous_score)
                st.session_state.assessment_questions = questions
                st.session_state.assessment_skill = selected
                st.session_state.assessment_origin = origin
                st.session_state.assessment_submitted = False
            questions = st.session_state.get("assessment_questions")
            if questions and st.session_state.get("assessment_skill") == selected:
                st.caption(st.session_state.get("assessment_origin", "Assessment"))
                if questions and questions[0].get("task_prompt"):
                    st.info("Practical task: " + questions[0]["task_prompt"])
                with st.form("skill_assessment_form"):
                    answers = {}
                    for idx, q in enumerate(questions):
                        answers[str(idx)] = st.radio(f"{idx+1}. {q['question']}", q["options"], key=f"answer_{st.session_state.get('assessment_skill')}_{idx}", index=None)
                    practical = st.text_area("Practical task response / project link (optional)", placeholder=questions[0].get("task_prompt", "Describe your solution and validation."), height=100)
                    submitted = st.form_submit_button("Submit and score assessment")
                if submitted:
                    answer_indices = {str(i): q["options"].index(answers[str(i)]) for i, q in enumerate(questions) if answers.get(str(i)) in q["options"]}
                    result = grade_quiz(questions, answer_indices)
                    result["practical_response"] = practical.strip()[:4000]
                    result["question_source"] = st.session_state.get("assessment_origin", "Assessment")
                    for item in passport["skills"]:
                        if item["skill"] == selected:
                            item["assessment_score"] = result["score"]
                            item["assessment_level"] = result["level"]
                            item["assessment_result"] = result
                            item["status"] = "Assessment completed · prototype"
                            item["limitations"] = list(dict.fromkeys(item.get("limitations", []) + [result["limitations"]]))
                            if practical.strip():
                                item["evidence"].append({"source_name": "Skill assessment", "source": "Skill assessment", "location": "Assessment submission", "quote": practical.strip()[:500], "explanation": "Candidate-submitted practical response. Not independently graded unless a configured assessment grader is used.", "evidence_type": "candidate_practical_response", "strength": "medium", "attribution_status": "candidate_submitted"})
                            break
                    st.session_state.assessment_last_result = result
                    st.session_state.published_token = ""
                    st.session_state.published_url = ""
                    st.success(f"Assessment scored {result['score']}/100. This is a prototype quiz score, not a certificate.")
                result = st.session_state.get("assessment_last_result")
                if result and st.session_state.get("assessment_skill") == selected:
                    st.metric("Latest score", f"{result['score']}/100")
                    st.write(f"Correct answers: {result['correct']} of {result['total']} · Suggested level: {result['level']}")
                    for i, q in enumerate(questions):
                        st.markdown(f"**{i+1}. {q['question']}**")
                        st.write(f"Correct answer: {q['options'][q['answer_index']]}")
                        st.caption(q.get("explanation", ""))
                        if q.get("task_prompt"): st.info(q["task_prompt"])
                    st.warning(result["limitations"])
        else:
            st.info("Add a skill or source in the sidebar and build the Passport first.")

    with tabs[2]:
        st.subheader("Evidence ledger")
        st.caption("Every evidence quote should be traceable to its source. Source presence is not authorship proof.")
        for skill in passport.get("skills", []):
            with st.expander(f"{skill['skill']} · {len(skill.get('evidence', []))} evidence item(s)"):
                for ev in skill.get("evidence", []):
                    st.markdown(f"**Source:** `{ev.get('source_name', ev.get('source', 'Unknown'))}`")
                    if ev.get("location"): st.caption("Location: " + ev["location"])
                    if ev.get("quote"): st.code(ev.get("quote", ""), language="text")
                    st.write(ev.get("explanation", ""))
                    st.caption(f"Type: {ev.get('evidence_type', 'unknown')} · Strength: {ev.get('strength', 'unknown')} · Attribution: {ev.get('attribution_status', 'unknown')}")
                    st.divider()

    with tabs[3]:
        st.subheader("Role gap analysis")
        st.caption("Transparent evidence-coverage estimate, not a hiring prediction.")
        if st.button("Analyze target role", key="analyze_role"):
            st.session_state.role_result = analyze_role(passport, st.session_state.get("last_target_role", ""), st.session_state.get("last_job_description", ""))
        role_result = st.session_state.role_result
        if role_result:
            st.metric("Evidence coverage estimate", f"{role_result.get('match_score', 0)}%")
            st.write(role_result.get("summary", ""))
            for item in role_result.get("requirements", []):
                with st.container(border=True):
                    st.markdown(f"**{item['skill']}** · {item['status']}")
                    st.write(item.get("reason", ""))
                    if item.get("matched_evidence"): st.caption("Evidence: " + "; ".join(item["matched_evidence"][:3]))
            if role_result.get("limitations"): st.info(" ".join(role_result["limitations"]))
        else:
            st.write("Enter a target role and job description in the sidebar, then analyze.")
        if st.button("Create 30-day learning plan", key="create_plan"):
            st.session_state.learning_plan = create_learning_plan(passport, st.session_state.role_result, st.session_state.get("last_target_role", ""), st.session_state.get("last_job_description", ""))
        plan = st.session_state.learning_plan
        if plan:
            st.subheader("30-day plan")
            for week in plan.get("weeks", []):
                st.markdown(f"### {week.get('week', 'Week')}: {week.get('theme', '')}")
                for task in week.get("tasks", []): st.markdown(f"- **{task.get('title', 'Task')}**: {task.get('action', '')}  \n  Deliverable: {task.get('deliverable', '')}")
            st.markdown("### Completion criteria")
            for item in plan.get("completion_criteria", []): st.write("☐ " + item)

    with tabs[4]:
        st.subheader("Publish a public Passport")
        st.write("Choose what is visible. Publishing creates a read-only snapshot accessible to anyone with the link. Do not include private information.")
        skill_names = [s["skill"] for s in passport.get("skills", [])]
        selected_skills = st.multiselect("Skills to publish", skill_names, default=skill_names, key="public_skill_selection")
        a, b = st.columns(2)
        with a:
            include_name = st.checkbox("Include candidate name", value=bool(passport.get("candidate", {}).get("name")), key="public_include_name")
            include_headline = st.checkbox("Include headline", value=True, key="public_include_headline")
        with b:
            include_evidence = st.checkbox("Include evidence quotes", value=True, key="public_include_evidence")
            include_source_links = st.checkbox("Include source links", value=False, key="public_include_links")
        share_passport = build_shareable_passport(passport, selected_skills, include_name, include_headline, include_evidence, include_source_links)
        share_passport["published_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        app_url = base_app_url()
        if not app_url:
            st.warning("Set PUBLIC_APP_URL to your deployed Streamlit app URL to create a link usable by other devices. Localhost links work only on this computer.")
        if st.button("Publish / update public snapshot", type="primary", key="publish_public"):
            token = publish_passport(share_passport)
            url = make_public_url(token, app_url)
            st.session_state.published_token = token
            st.session_state.published_url = url
        if st.session_state.published_token:
            if st.session_state.published_url:
                st.success("Public snapshot saved. Test the link in a private/incognito window before your demo.")
                st.code(st.session_state.published_url)
                st.image(qr_png(st.session_state.published_url), caption="Scan to open the public Passport", width=220)
                st.download_button("Download QR code (PNG)", qr_png(st.session_state.published_url), file_name="skill_passport_qr.png", mime="image/png")
                st.link_button("Open public verification page", st.session_state.published_url)
            else:
                st.error("Snapshot saved locally, but no public URL is configured. Set PUBLIC_APP_URL and publish again.")
            if st.button("Revoke this published link", key="revoke_public"):
                revoke_passport(st.session_state.published_token)
                st.session_state.published_token = ""
                st.session_state.published_url = ""
                st.success("The link was revoked in this database.")
        st.caption("Prototype storage uses SQLite. On ephemeral hosting, records may be lost on restart or redeploy. For durable public verification across deployments, connect a managed database before production use.")

    with tabs[5]:
        st.subheader("Recruiter preview & exports")
        skill_names = [s.get("skill", "") for s in passport.get("skills", []) if s.get("skill")]
        selected = st.multiselect("Skills to include in export", skill_names, default=skill_names, key="export_skills")
        c1, c2 = st.columns(2)
        with c1:
            include_name = st.checkbox("Include name", value=bool(passport.get("candidate", {}).get("name")), key="export_name")
            include_headline = st.checkbox("Include headline", value=True, key="export_headline")
        with c2:
            include_evidence = st.checkbox("Include evidence", value=True, key="export_evidence")
            include_links = st.checkbox("Include source links", value=False, key="export_links")
        include_role = st.checkbox("Include role analysis", value=True, key="export_role")
        include_plan = st.checkbox("Include learning plan", value=False, key="export_plan")
        filtered = build_shareable_passport(passport, selected, include_name, include_headline, include_evidence, include_links)
        html = passport_html(filtered, st.session_state.role_result if include_role else None, st.session_state.learning_plan if include_plan else None)
        st.components.v1.html(html, height=550, scrolling=True)
        st.download_button("Download filtered Passport (HTML)", html, "skill_passport.html", "text/html")
        st.download_button("Download filtered Passport (Markdown)", passport_markdown(filtered, st.session_state.role_result if include_role else None, st.session_state.learning_plan if include_plan else None), "skill_passport.md", "text/markdown")
        st.download_button("Download filtered Passport (JSON)", json.dumps(filtered, indent=2, ensure_ascii=False), "skill_passport.json", "application/json")
else:
    st.markdown("### Build your evidence-backed profile")
    col1, col2, col3 = st.columns(3)
    col1.markdown("#### 🧪 Assess skills\nTake adaptive quizzes and receive practical task prompts.")
    col2.markdown("#### 🔗 Attach project proof\nImport public GitHub repositories and supporting documents.")
    col3.markdown("#### 📱 Share the Passport\nPublish a filtered profile with a public URL and QR code.")
    st.markdown("**Demo flow:** create profile → add skill → take assessment → attach project → publish → open the QR link as a recruiter.")
