from flask import jsonify, session, request
from datetime import datetime
# ===== جلب بيانات اليوم =====
def get_patients():

    if "role" not in session:
        return jsonify([]), 401

    conn = db_connect()
    c = conn.cursor()

    today = datetime.now().strftime("%Y-%m-%d")

    section = request.args.get("section", "all")

    if section == "all":

        c.execute(
            "SELECT * FROM patients WHERE date=? ORDER BY id ASC",
            (today,)
        )

    else:

        c.execute(
            "SELECT * FROM patients WHERE date=? AND section=? ORDER BY id ASC",
            (today, section)
        )

    data = c.fetchall()

    conn.close()

    return jsonify([dict(row) for row in data])