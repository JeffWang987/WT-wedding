import os
import sqlite3
from datetime import datetime

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

from gold_strategy import get_gold_strategy_data

app = Flask(__name__)
DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "data.db"))


def _get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_db():
    conn = _get_db()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS investment_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invest_date TEXT NOT NULL,
            amount_cny REAL NOT NULL,
            grams REAL,
            price_cny_per_gram REAL,
            note TEXT DEFAULT '',
            created_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def _parse_origins():
    origins = os.environ.get("ALLOWED_ORIGINS", "*").strip()
    if origins == "*":
        return "*"
    return [item.strip() for item in origins.split(",") if item.strip()]


def _build_records_payload(rows):
    records = []
    cumulative_invested = 0.0
    cumulative_grams = 0.0
    chart_dates = []
    chart_cumulative = []
    monthly_totals = {}

    for row in rows:
        item = dict(row)
        item["amount_cny"] = float(item["amount_cny"])
        item["grams"] = float(item["grams"]) if item["grams"] is not None else None
        item["price_cny_per_gram"] = float(item["price_cny_per_gram"]) if item["price_cny_per_gram"] is not None else None
        records.append(item)

        cumulative_invested += item["amount_cny"]
        if item["grams"] is not None:
            cumulative_grams += item["grams"]
        chart_dates.append(item["invest_date"])
        chart_cumulative.append(round(cumulative_invested, 2))
        month_key = item["invest_date"][:7]
        monthly_totals[month_key] = round(monthly_totals.get(month_key, 0.0) + item["amount_cny"], 2)

    avg_cost = round(cumulative_invested / cumulative_grams, 4) if cumulative_grams > 0 else None

    return {
        "records": records,
        "summary": {
            "record_count": len(records),
            "total_invested_cny": round(cumulative_invested, 2),
            "total_grams": round(cumulative_grams, 4),
            "average_cost_cny_per_gram": avg_cost,
        },
        "chart": {
            "dates": chart_dates,
            "cumulative_invested_cny": chart_cumulative,
            "monthly_labels": list(monthly_totals.keys()),
            "monthly_totals_cny": list(monthly_totals.values()),
        },
    }


_ensure_db()
CORS(app, resources={r"/api/*": {"origins": _parse_origins()}})


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/calculate", methods=["POST"])
def calculate():
    payload = request.get_json(silent=True) or {}
    base_budget = payload.get("base_budget_cny", 1000)

    try:
        base_budget = float(base_budget)
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "请输入有效的预算数字。"}), 400

    if base_budget <= 0:
        return jsonify({"ok": False, "error": "预算必须大于 0。"}), 400

    try:
        result = get_gold_strategy_data(base_budget_cny=base_budget, period="1y")
        return jsonify({"ok": True, "result": result})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.route("/api/records", methods=["GET"])
def list_records():
    conn = _get_db()
    rows = conn.execute(
        """
        SELECT id, invest_date, amount_cny, grams, price_cny_per_gram, note, created_at
        FROM investment_records
        ORDER BY invest_date ASC, id ASC
        """
    ).fetchall()
    conn.close()
    payload = _build_records_payload(rows)
    return jsonify({"ok": True, **payload})


@app.route("/api/records", methods=["POST"])
def create_record():
    payload = request.get_json(silent=True) or {}
    invest_date = str(payload.get("invest_date", "")).strip()
    note = str(payload.get("note", "")).strip()

    try:
        datetime.strptime(invest_date, "%Y-%m-%d")
    except Exception:
        return jsonify({"ok": False, "error": "投资日期格式必须是 YYYY-MM-DD。"}), 400

    try:
        amount_cny = float(payload.get("amount_cny"))
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "请输入有效的投资金额。"}), 400
    if amount_cny <= 0:
        return jsonify({"ok": False, "error": "投资金额必须大于 0。"}), 400

    grams_raw = payload.get("grams", None)
    grams = None
    if grams_raw not in (None, ""):
        try:
            grams = float(grams_raw)
        except (TypeError, ValueError):
            return jsonify({"ok": False, "error": "克重必须是数字。"}), 400
        if grams <= 0:
            return jsonify({"ok": False, "error": "克重必须大于 0。"}), 400

    price_raw = payload.get("price_cny_per_gram", None)
    price_cny_per_gram = None
    if price_raw not in (None, ""):
        try:
            price_cny_per_gram = float(price_raw)
        except (TypeError, ValueError):
            return jsonify({"ok": False, "error": "买入单价必须是数字。"}), 400
        if price_cny_per_gram <= 0:
            return jsonify({"ok": False, "error": "买入单价必须大于 0。"}), 400

    if grams is None and price_cny_per_gram is not None:
        grams = round(amount_cny / price_cny_per_gram, 6)
    if price_cny_per_gram is None and grams is not None:
        price_cny_per_gram = round(amount_cny / grams, 6)

    created_at = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    conn = _get_db()
    cur = conn.execute(
        """
        INSERT INTO investment_records (invest_date, amount_cny, grams, price_cny_per_gram, note, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (invest_date, amount_cny, grams, price_cny_per_gram, note, created_at),
    )
    conn.commit()
    new_id = cur.lastrowid
    row = conn.execute(
        """
        SELECT id, invest_date, amount_cny, grams, price_cny_per_gram, note, created_at
        FROM investment_records
        WHERE id = ?
        """,
        (new_id,),
    ).fetchone()
    conn.close()
    return jsonify({"ok": True, "record": dict(row)})


@app.route("/api/records/<int:record_id>", methods=["DELETE"])
def delete_record(record_id):
    conn = _get_db()
    cur = conn.execute("DELETE FROM investment_records WHERE id = ?", (record_id,))
    conn.commit()
    deleted = cur.rowcount
    conn.close()
    if deleted == 0:
        return jsonify({"ok": False, "error": "记录不存在。"}), 404
    return jsonify({"ok": True, "deleted_id": record_id})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
