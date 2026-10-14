import html
import json

def passport_markdown(passport, role_result=None, learning_plan=None):
    candidate = passport.get("candidate", {})
    lines = [
        "# Skill Passport",
        "",
        f"**Candidate:** {candidate.get('name') or 'Not provided'}",
        f"**Headline:** {candidate.get('headline') or 'Not provided'}",
        f"**Generated:** {passport.get('created_at', '')}",
        "",
        "## Skills and evidence",
    ]
    for skill in passport.get("skills", []):
        lines += [
            "",
            f"### {skill['skill']}",
            f"- **Level:** {skill.get('level', 'Not assessed')}",
            f"- **Status:** {skill.get('status', 'Unverified')}",
            f"- **Confidence:** {skill.get('confidence', 0):.0%}",
            f"- **Assessment score:** {skill.get('assessment_score', 'Not assessed')}{'/100' if skill.get('assessment_score') is not None else ''}",
            f"- **Summary:** {skill.get('summary', '')}",
        ]
        for ev in skill.get("evidence", []):
            lines.append(f"- **Evidence ({ev.get('source_name', 'source')}):** “{ev.get('quote', '')}”")
            if ev.get("explanation"):
                lines.append(f"  - Interpretation: {ev['explanation']}")
    if role_result:
        lines += ["", "## Role analysis", f"**Role match estimate:** {role_result.get('match_score', 0)}%", "", role_result.get("summary", "")]
        for item in role_result.get("requirements", []):
            lines.append(f"- **{item['skill']}**: {item['status']} - {item.get('reason', '')}")
    if learning_plan:
        lines += ["", "## 30-day learning plan"]
        for week in learning_plan.get("weeks", []):
            lines += ["", f"### {week.get('week')}: {week.get('theme')}"]
            for task in week.get("tasks", []):
                lines.append(f"- **{task.get('title')}**: {task.get('action')} Deliverable: {task.get('deliverable', '')}")
    lines += ["", "## Limitations"]
    for note in passport.get("notes", []):
        lines.append(f"- {note}")
    lines += [
        "",
        "> This prototype summarizes submitted sources. It is not a formal certification, independent identity check, or hiring prediction.",
    ]
    return "\n".join(lines)

def passport_html(passport, role_result=None, learning_plan=None):
    def esc(value):
        return html.escape(str(value or ""))
    candidate = passport.get("candidate", {})
    skill_cards = []
    for skill in passport.get("skills", []):
        evidence_html = "".join(
            f"<li><strong>{esc(ev.get('source_name', 'Source'))}</strong><br><q>{esc(ev.get('quote', ''))}</q><p>{esc(ev.get('explanation', ''))}</p></li>"
            for ev in skill.get("evidence", [])
        )
        skill_cards.append(
            f"<article class='skill'><h3>{esc(skill['skill'])}</h3>"
            f"<p><strong>Level:</strong> {esc(skill.get('level', 'Not assessed'))} &nbsp; "
            f"<strong>Status:</strong> {esc(skill.get('status', 'Unverified'))}</p>"
            f"<p><strong>Assessment score:</strong> {esc(str(skill.get('assessment_score')) + '/100' if skill.get('assessment_score') is not None else 'Not assessed')} "
            f"<span class='muted'>{esc(skill.get('assessment_level', ''))}</span></p>"
            f"<p>{esc(skill.get('summary', ''))}</p><ul>{evidence_html}</ul></article>"
        )
    role_html = ""
    if role_result:
        items = "".join(
            f"<li><strong>{esc(item['skill'])}</strong>: {esc(item['status'])}<br>{esc(item.get('reason', ''))}</li>"
            for item in role_result.get("requirements", [])
        )
        role_html = f"<section><h2>Role analysis</h2><p><strong>Evidence match estimate: {role_result.get('match_score', 0)}%</strong></p><ul>{items}</ul></section>"
    plan_html = ""
    if learning_plan:
        weeks = ""
        for week in learning_plan.get("weeks", []):
            tasks = "".join(f"<li><strong>{esc(t.get('title'))}:</strong> {esc(t.get('action'))}</li>" for t in week.get("tasks", []))
            weeks += f"<h3>{esc(week.get('week'))}: {esc(week.get('theme'))}</h3><ul>{tasks}</ul>"
        plan_html = f"<section><h2>30-day learning plan</h2>{weeks}</section>"
    notes = "".join(f"<li>{esc(n)}</li>" for n in passport.get("notes", []))
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Skill Passport - {esc(candidate.get('name') or 'Candidate')}</title>
<style>
:root{{color-scheme:light}}body{{font-family:Arial,sans-serif;max-width:1000px;margin:0 auto;padding:28px;color:#18202b;background:#f5f7fa;line-height:1.55}}
header,.skill,section{{background:white;border:1px solid #dce2ea;border-radius:14px;padding:20px;margin:14px 0}}
h1{{margin-bottom:4px}}h2{{margin-top:0}}.muted{{color:#5d6878;font-size:.92rem}}q{{display:block;background:#f4f6f9;padding:10px;border-radius:8px;overflow-wrap:anywhere}}
footer{{margin-top:24px;color:#5d6878;font-size:.9rem}}@media print{{body{{background:white;padding:0}}header,.skill,section{{break-inside:avoid}}}}
</style></head><body>
<header><h1>Skill Passport</h1><h2>{esc(candidate.get('name') or 'Candidate')}</h2>
<p>{esc(candidate.get('headline'))}</p><p class="muted">Generated {esc(passport.get('created_at', ''))} · ID {esc(passport.get('passport_id', ''))}</p></header>
<section><h2>Evidence-backed skills</h2>{''.join(skill_cards) if skill_cards else '<p>No skill claims were extracted.</p>'}</section>
{role_html}{plan_html}
<section><h2>Important limitations</h2><ul>{notes}</ul></section>
<footer>This prototype summarizes submitted sources. It is not a formal certification, independent identity check, or hiring prediction. Review before sharing.</footer>
</body></html>"""
