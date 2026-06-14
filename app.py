#!/usr/bin/env python3
"""
AI Speed Dating — Serveur autonome
Questionnaire + Matching + Affichage, tout en un
"""
from flask import Flask, request, jsonify, render_template, redirect, url_for
import json, os, time, threading, subprocess

app = Flask(__name__)
DATA_FILE    = "data/responses.json"
RESULTS_FILE = "data/results.json"
os.makedirs("data", exist_ok=True)

def load_responses():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE) as f:
        return json.load(f)

def save_responses(responses):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(responses, f, ensure_ascii=False, indent=2)

# ── Formulaire ──────────────────────────────────────────────────────────────
@app.route("/")
def form():
    count = len(load_responses())
    return render_template("form.html", count=count)

@app.route("/submit", methods=["POST"])
def submit():
    data = request.get_json()
    responses = load_responses()

    # Vérifie doublons par prénom+nom
    existing = [r for r in responses if
        r["nom"].lower() == data.get("nom","").lower() and
        r["nom_famille"].lower() == data.get("nom_famille","").lower()]
    if existing:
        return jsonify({"ok": False, "error": "Ce profil existe déjà."})

    responses.append({
        "id":          len(responses) + 1,
        "nom":         data.get("nom", "").strip(),
        "nom_famille": data.get("nom_famille", "").strip(),
        "age":         data.get("age", "").strip(),
        "sexe":        data.get("sexe", "").strip(),
        "telephone":   data.get("telephone", "").strip(),
        "resume_ia":   data.get("resume_ia", "").strip(),
        "timestamp":   time.strftime("%Y-%m-%d %H:%M:%S"),
    })
    save_responses(responses)
    return jsonify({"ok": True, "total": len(responses)})

@app.route("/merci")
def merci():
    return render_template("merci.html")

# ── Résultats ────────────────────────────────────────────────────────────────
@app.route("/results")
def results_page():
    return render_template("results.html")

@app.route("/results.json")
def results_json():
    if not os.path.exists(RESULTS_FILE):
        return jsonify({"error": "Pas encore de résultats"}), 404
    with open(RESULTS_FILE) as f:
        return jsonify(json.load(f))

# ── Admin ────────────────────────────────────────────────────────────────────
@app.route("/admin")
def admin():
    responses = load_responses()
    results_exist = os.path.exists(RESULTS_FILE)
    return render_template("admin.html", responses=responses, results_exist=results_exist)

@app.route("/admin/run-matching", methods=["POST"])
def run_matching():
    def do_match():
        subprocess.run(["python3", "matcher_v2.py"], cwd=os.path.dirname(os.path.abspath(__file__)))
    threading.Thread(target=do_match).start()
    return jsonify({"ok": True, "message": "Matching lancé en arrière-plan…"})

@app.route("/admin/delete/<int:pid>", methods=["POST"])
def delete_profile(pid):
    responses = load_responses()
    responses = [r for r in responses if r["id"] != pid]
    # Réindexer
    for i, r in enumerate(responses):
        r["id"] = i + 1
    save_responses(responses)
    return redirect(url_for("admin"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=False)
