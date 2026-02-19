"""Flask route definitions."""

import json
import time

from flask import (
    Blueprint,
    Response,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)

from kaitori_scraper.config.collection import get_collection_by_ids
from web.scrape_runner import get_state, start_scrape

bp = Blueprint("main", __name__)


@bp.route("/")
def dashboard():
    items = get_collection_by_ids(None)
    state = get_state()
    return render_template("dashboard.html", items=items, state=state)


@bp.route("/scrape", methods=["POST"])
def scrape():
    mode = request.form.get("mode", "both")
    if mode not in ("both", "fastbuy", "onechome"):
        mode = "both"
    start_scrape(mode)
    return redirect(url_for("main.dashboard"))


@bp.route("/results")
def results():
    state = get_state()
    if not state.results:
        return redirect(url_for("main.dashboard"))
    return render_template("results.html", state=state)


@bp.route("/api/progress")
def progress_stream():
    def generate():
        last_log_count = 0
        while True:
            state = get_state()
            new_logs = state.log_lines[last_log_count:]
            last_log_count = len(state.log_lines)
            data = json.dumps(
                {
                    "status": state.status,
                    "progress": round(state.progress * 100, 1),
                    "phase": state.phase,
                    "logs": new_logs,
                },
                ensure_ascii=False,
            )
            yield f"data: {data}\n\n"
            if state.status in ("completed", "error", "idle"):
                break
            time.sleep(1)

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@bp.route("/api/status")
def status():
    state = get_state()
    return jsonify(
        {
            "status": state.status,
            "progress": round(state.progress * 100, 1),
            "phase": state.phase,
            "has_results": bool(state.results),
        }
    )


@bp.route("/download/csv")
def download_csv():
    state = get_state()
    if not state.csv_content:
        return redirect(url_for("main.dashboard"))
    ts = state.completed_at.strftime("%Y%m%d_%H%M%S") if state.completed_at else "report"
    return Response(
        state.csv_content.encode("utf-8-sig"),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=price_report_{ts}.csv"},
    )


@bp.route("/download/txt")
def download_txt():
    state = get_state()
    if not state.text_content:
        return redirect(url_for("main.dashboard"))
    ts = state.completed_at.strftime("%Y%m%d_%H%M%S") if state.completed_at else "report"
    return Response(
        state.text_content.encode("utf-8"),
        mimetype="text/plain; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename=price_report_{ts}.txt"},
    )
