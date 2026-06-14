#!/usr/bin/env python3
"""Matcher v2 — lit depuis data/responses.json au lieu de Google Sheets"""

import json, os, sys, time
import anthropic

ANTHROPIC_API_KEY = ***"ANTHROPIC_API_KEY", "")
DATA_FILE    = "data/responses.json"
RESULTS_FILE = "data/results.json"

def load_profiles():
    if not os.path.exists(DATA_FILE):
        print("❌ data/responses.json introuvable"); sys.exit(1)
    with open(DATA_FILE) as f:
        return json.load(f)

def rank_for_person(client, person, candidates):
    candidates_text = "\n\n".join([
        f"[ID:{c['id']}] {c['nom']} {c['nom_famille']}, {c['age']} ans :\n{c['resume_ia']}"
        for c in candidates
    ])
    prompt = f"""Tu es un expert en compatibilité romantique.

PROFIL DE {person['nom'].upper()} {person['nom_famille'].upper()}, {person['age']} ans :
{person['resume_ia']}

Classe ces {len(candidates)} candidats du plus au moins compatible.

Règle importante : la compatibilité religieuse et culturelle est un facteur primordial. Si les profils indiquent des niveaux de pratique ou des valeurs religieuses/culturelles incompatibles (ex: très religieux vs laïque, modes de vie fondamentalement différents), réduis le score de manière significative (-20 à -40 points). À l'inverse, une compatibilité religieuse et culturelle forte booste le score.

Réponds UNIQUEMENT en JSON :
{{"classement": [{{"id": <id>, "score": <0-100>, "raison": "<une phrase>"}}]}}
Tous les IDs doivent apparaître exactement une fois.

CANDIDATS :
{candidates_text}"""

    r = client.messages.create(
        model="claude-sonnet-4-6", max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )
    text = r.content[0].text.strip()
    s, e = text.find('{'), text.rfind('}') + 1
    return json.loads(text[s:e])["classement"]

def main():
    if not ANTHROPIC_API_KEY:
        ***"❌ ANTHROPIC_API_KEY manquant"); sys.exit(1)

    profiles = load_profiles()
    client   = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    hommes = [p for p in profiles if p["sexe"].lower() in ("masculin","homme","m","male")]
    femmes = [p for p in profiles if p["sexe"].lower() in ("féminin","feminin","femme","f","female")]

    print(f"✓ {len(hommes)}H × {len(femmes)}F — {len(hommes)+len(femmes)} appels\n")

    scores_h, scores_f = {}, {}

    for h in hommes:
        print(f"  {h['nom']}...", end=" ", flush=True)
        try:
            for item in rank_for_person(client, h, femmes):
                scores_h[(h["id"], item["id"])] = {"score": item["score"], "raison": item["raison"]}
            print("✓")
        except Exception as e:
            print(f"ERREUR ({e})")
        time.sleep(0.5)

    for f in femmes:
        print(f"  {f['nom']}...", end=" ", flush=True)
        try:
            for item in rank_for_person(client, f, hommes):
                scores_f[(f["id"], item["id"])] = {"score": item["score"], "raison": item["raison"]}
            print("✓")
        except Exception as e:
            print(f"ERREUR ({e})")
        time.sleep(0.5)

    all_scores = []
    for h in hommes:
        for f in femmes:
            hd = scores_h.get((h["id"], f["id"]), {"score": 50, "raison": ""})
            fd = scores_f.get((f["id"], h["id"]), {"score": 50, "raison": ""})
            avg = round((hd["score"] + fd["score"]) / 2)
            all_scores.append({
                "profil_a": h, "profil_b": f, "score": avg,
                "score_h": hd["score"], "score_f": fd["score"],
                "raison": hd["raison"] or fd["raison"],
                "mutual": hd["score"] >= 70 and fd["score"] >= 70,
            })

    all_scores.sort(key=lambda x: x["score"], reverse=True)

    top3 = {}
    for e in all_scores:
        for role in ("profil_a","profil_b"):
            p = e[role]; o = e["profil_b"] if role=="profil_a" else e["profil_a"]
            if p["id"] not in top3: top3[p["id"]] = {"personne": p, "top3": []}
            if len(top3[p["id"]]["top3"]) < 3:
                top3[p["id"]]["top3"].append({"match": o, "score": e["score"], "raison": e["raison"], "mutual": e["mutual"]})

    mutuals = [e for e in all_scores if e["mutual"]]
    results = {
        "top_matchs": all_scores[:20],
        "best_per_person": [{"personne": v["personne"], "meilleur_match": v["top3"][0]["match"] if v["top3"] else None,
            "score": v["top3"][0]["score"] if v["top3"] else 0, "raison": v["top3"][0]["raison"] if v["top3"] else "",
            "top3": v["top3"]} for v in top3.values()],
        "mutual_matches": mutuals, "total_profils": len(profiles),
        "stats": {"hommes": len(hommes), "femmes": len(femmes), "mutuals": len(mutuals)}
    }

    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n✅ {len(mutuals)} mutuels · Top: {all_scores[0]['profil_a']['nom']} × {all_scores[0]['profil_b']['nom']} ({all_scores[0]['score']}%)")

if __name__ == "__main__":
    main()
