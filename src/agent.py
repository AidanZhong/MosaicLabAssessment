# -*- coding: utf-8 -*-
"""
@author: Aidan
@project: MosaicLabAssessment
@filename: agent
"""
import json
import os
from pathlib import Path

import anthropic
import pandas as pd
from dotenv import load_dotenv

from config import LOSS_INDICATOR_FILE, PIPLINE_FILE, WEEKLY_PREMIUM_FILE, WEEKLY_SUBMISSION_FILE
from src.detect import detect_all

load_dotenv()


def read_data():
    loss_indicator = pd.read_csv(LOSS_INDICATOR_FILE, parse_dates=["week_ending"])
    pipeline = pd.read_csv(PIPLINE_FILE, parse_dates=["week_ending"])
    weekly_premium = pd.read_csv(WEEKLY_PREMIUM_FILE, parse_dates=["week_ending"])
    weekly_submissions = pd.read_csv(WEEKLY_SUBMISSION_FILE, parse_dates=["week_ending"])

    for df in [loss_indicator, pipeline, weekly_premium, weekly_submissions]:
        df.sort_values(by="week_ending", inplace=True)
    return loss_indicator, pipeline, weekly_premium, weekly_submissions


def build_prompt(week_ending, signals, premium_df):
    prompts_dir = Path(__file__).parent / "prompts"
    system_prompt = (prompts_dir / "system_prompt.txt").read_text()
    user_prompt = (prompts_dir / "user_prompt.txt").read_text()

    signals_text = ""
    for signal in signals:
        signals_text += f"""
        Title: {signal["title"]}
        Detail: {signal["detail"]}
        Action: {signal["action"]}
        ---"""

    lobs = premium_df["lob"].unique()
    snapshot_lines = []
    for lob in lobs:
        lob_data = premium_df[premium_df["lob"] == lob]
        ytd_att = lob_data.iloc[-1]["ytd_actual"] / lob_data.iloc[-1]["ytd_plan"]
        snapshot_lines.append(f"{lob}: YTD attainment {ytd_att:.0%}")
    portfolio_summary = "\n".join(snapshot_lines)

    # Fill placeholders
    user_prompt = user_prompt.format(
        week_ending=week_ending,
        signals=signals_text,
        portfolio_summary=portfolio_summary,
    )

    return system_prompt, user_prompt


def call_claude(system_prompt, user_prompt):
    env_path = Path(__file__).parent.parent / ".env"
    api_key = None
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("ANTHROPIC_API_KEY="):
                api_key = line.split("=", 1)[1].strip()
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not found in .env file.")

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return message.content[0].text


def save_outputs(narrative):
    output_dir = Path(__file__).parent.parent / "output"
    output_dir.mkdir(exist_ok=True)
    (output_dir / "narrative.md").write_text(narrative)


def save_json(narrative, signals, premium_df, submission_df):
    weeks = [w.strftime("%b %d") for w in premium_df["week_ending"].unique()]
    lobs = premium_df["lob"].unique()

    gwp_lobs = {}
    for lob in lobs:
        lob_df = premium_df[premium_df["lob"] == lob]
        gwp_lobs[lob] = {
            "actual": lob_df["actual_gwp"].tolist(),
            "plan": lob_df["plan_gwp"].tolist(),
        }

    hit_rate_lobs = {}
    for lob in lobs:
        lob_data = submission_df[submission_df["lob"] == lob]
        hit_rate = lob_data["bound_count"] / (lob_data["bound_count"] + lob_data["quoted_count"] + lob_data["declined_count"] +
                                           lob_data["ntu_count"])
        hit_rate_lobs[lob] = hit_rate.round(2).tolist()

    # Otherwise, the rank is not serializable to JSON
    clean_signals = [
        {**s, "rank": float(s["rank"])} for s in signals
    ]

    output = {
        "narrative": narrative,
        "signals": clean_signals,
        "charts": {
            "gwp": {"weeks": weeks, "lobs": gwp_lobs},
            "hit_rate": {"weeks": weeks, "lobs": hit_rate_lobs},
        }
    }

    output_dir = Path(__file__).parent.parent / "output"
    output_dir.mkdir(exist_ok=True)
    (output_dir / "analysis.json").write_text(json.dumps(output, indent=2))
    return output


def generate_dashboard(data: dict):
    json_str = json.dumps(data)

    signal_cards = ""
    for s in data["signals"]:
        if s["type"] == "concern":
            border = "#e74c3c"
            tag_bg = "#e74c3c"
            tag = "CONCERN"
        else:
            border = "#27ae60"
            tag_bg = "#27ae60"
            tag = "OPPORTUNITY"
        rank_val = round(s['rank'], 2) if isinstance(s['rank'], float) else s['rank']
        signal_cards += f"""
        <div class="signal-card" style="border-left: 4px solid {border}">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px">
            <span class="signal-tag" style="background:{tag_bg}">{tag}</span>
            <span style="font-size:11px; color:#888; font-weight:600">severity {rank_val}</span>
          </div>
          <h3>{s['title']}</h3>
          <p>{s['detail']}</p>
          <p class="action"><strong>Action:</strong> {s['action']}</p>
        </div>"""

    narrative_html = data["narrative"].replace("\n\n", "</p><p>")
    lobs = list(data["charts"]["gwp"]["lobs"].keys())
    lob_options = "".join(f'<option value="{l}">{l}</option>' for l in lobs)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Mosaic Weekly Performance</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: 'Segoe UI', sans-serif; background: #f4f4f8; color: #1a1a2e; }}
    header {{ background: #2c1033; color: white; padding: 20px 40px; display: flex; justify-content: space-between; align-items: center; }}
    header h1 {{ font-size: 22px; letter-spacing: 1px; }}
    header h1 span {{ color: #c77dff; }}
    header p {{ font-size: 13px; opacity: 0.8; }}
    .main {{ max-width: 1300px; margin: 0 auto; padding: 32px 24px; }}
    .section-title {{ font-size: 16px; font-weight: 700; color: #2c1033; margin: 28px 0 12px; border-left: 4px solid #7b2d8b; padding-left: 10px; }}
    .signals-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px; }}
    .signal-card {{ background: white; border-radius: 8px; padding: 18px; box-shadow: 0 1px 4px rgba(0,0,0,.08); }}
    .signal-tag {{ display: inline-block; font-size: 10px; font-weight: 700; letter-spacing: 1px; color: white; padding: 2px 8px; border-radius: 4px; margin-bottom: 8px; }}
    .signal-card h3 {{ font-size: 14px; margin-bottom: 8px; }}
    .signal-card p {{ font-size: 13px; color: #555; line-height: 1.6; margin-bottom: 6px; }}
    .action {{ background: #f4f4f8; padding: 8px 10px; border-radius: 6px; }}
    .charts-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }}
    @media (max-width: 800px) {{ .charts-row {{ grid-template-columns: 1fr; }} }}
    .card {{ background: white; border-radius: 10px; padding: 20px; box-shadow: 0 1px 4px rgba(0,0,0,.08); }}
    .card-title {{ font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: .5px; color: #888; margin-bottom: 14px; }}
    select {{ padding: 5px 10px; border: 1px solid #ddd; border-radius: 6px; font-size: 13px; margin-bottom: 14px; }}
    .chart-wrap {{ position: relative; height: 260px; }}
    .narrative-box {{ background: white; border-radius: 10px; padding: 24px; box-shadow: 0 1px 4px rgba(0,0,0,.08); line-height: 1.8; font-size: 15px; }}
    .narrative-box p {{ margin-bottom: 12px; }}
    .heatmap-wrap {{ overflow-x: auto; }}
    table {{ border-collapse: collapse; font-size: 12px; width: 100%; }}
    th {{ background: #f0e8f5; color: #2c1033; padding: 6px 10px; text-align: center; font-weight: 600; white-space: nowrap; }}
    td {{ padding: 6px 10px; text-align: center; border: 1px solid #eee; font-weight: 600; }}
    .lob-label {{ text-align: left; background: #f0e8f5; font-weight: 600; white-space: nowrap; }}
  </style>
</head>
<body>
<header>
  <h1>Mos<span>AI</span>c — Underwriting Performance</h1>
  <p>Week ending {data['charts']['gwp']['weeks'][-1]}</p>
</header>
<main class="main">

  <div class="section-title">Performance Signals</div>
  <div class="signals-grid">{signal_cards}</div>

  <div class="section-title">Charts</div>
  <div class="charts-row">
    <div class="card">
      <div class="card-title">GWP vs Plan</div>
      <select id="lobSelect" onchange="updateGwp(this.value)">{lob_options}</select>
      <div class="chart-wrap"><canvas id="gwpChart"></canvas></div>
    </div>
    <div class="card">
      <div class="card-title">Hit Rate Heatmap (LoB × Week)</div>
      <div class="heatmap-wrap"><table id="heatmap"></table></div>
    </div>
  </div>

  <div class="section-title">Executive Narrative</div>
  <div class="narrative-box"><p>{narrative_html}</p></div>

</main>
<script>
const DATA = {json_str};
const WEEKS = DATA.charts.gwp.weeks;
const LOBS  = Object.keys(DATA.charts.gwp.lobs);

// GWP Chart
let gwpChart = null;
function updateGwp(lob) {{
  const ctx = document.getElementById('gwpChart').getContext('2d');
  if (gwpChart) gwpChart.destroy();
  gwpChart = new Chart(ctx, {{
    type: 'line',
    data: {{
      labels: WEEKS,
      datasets: [
        {{ label: 'Actual', data: DATA.charts.gwp.lobs[lob].actual, borderColor: '#7b2d8b', backgroundColor: 'rgba(123,45,139,.1)', fill: true, tension: 0.3, borderWidth: 2 }},
        {{ label: 'Plan',   data: DATA.charts.gwp.lobs[lob].plan,   borderColor: '#aaa', borderDash: [5,4], fill: false, borderWidth: 1.5, pointRadius: 0 }}
      ]
    }},
    options: {{ responsive: true, maintainAspectRatio: false,
      scales: {{ y: {{ ticks: {{ callback: v => '£' + (v/1000).toFixed(0) + 'k' }} }}, x: {{ grid: {{ display: false }} }} }}
    }}
  }});
}}
updateGwp(LOBS[0]);
document.getElementById('lobSelect').value = LOBS[0];

// Hit Rate Heatmap
function buildHeatmap() {{
  const table = document.getElementById('heatmap');
  let html = '<thead><tr><th>LoB</th>';
  WEEKS.forEach(w => html += `<th>${{w}}</th>`);
  html += '</tr></thead><tbody>';
  LOBS.forEach(lob => {{
    html += `<tr><td class="lob-label">${{lob}}</td>`;
    DATA.charts.hit_rate.lobs[lob].forEach(v => {{
      const pct = Math.round(v * 100);
      const intensity = v / 0.4;
      const r = Math.round(255 - intensity * 132);
      const g = Math.round(255 - intensity * 210);
      const b = Math.round(255 - intensity * 116);
      const text = intensity > 0.6 ? 'white' : '#333';
      html += `<td style="background:rgb(${{r}},${{g}},${{b}});color:${{text}}">${{pct}}%</td>`;
    }});
    html += '</tr>';
  }});
  html += '</tbody>';
  table.innerHTML = html;
}}
buildHeatmap();
</script>
</body>
</html>"""

    output_dir = Path(__file__).parent.parent / "output"
    output_dir.mkdir(exist_ok=True)
    (output_dir / "dashboard.html").write_text(html, encoding="utf-8")


def main():
    loss, pipeline, premium, submissions = read_data()
    signals = detect_all(premium, submissions, loss)
    week_ending = premium["week_ending"].max().strftime("%Y-%m-%d")
    system_prompt, user_prompt = build_prompt(week_ending, signals, premium)
    narrative = call_claude(system_prompt, user_prompt)
    save_outputs(narrative)
    json_data = save_json(narrative, signals, premium, submissions)
    generate_dashboard(json_data)

if __name__ == "__main__":
    main()
