from flask import Flask, request, redirect, url_for, render_template, flash
import json
import os

app = Flask(__name__)
app.secret_key = "demo-key" #change key for security purposes

BLACKLIST_FILE = "data/blacklist.json"

def load_blacklist():
    if not os.path.exists(BLACKLIST_FILE):
        return []
    with open(BLACKLIST_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_blacklist(lst):
    with open(BLACKLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(lst, f, indent=2)


@app.route("/")
def index():
    bl = load_blacklist()
    return render_template("settings.html", blacklist=bl)

@app.route("/add", methods=["POST"])
def add():
    item = request.form.get("item", "").strip()
    if not item:
        flash("Empty entry not added.")
        return redirect(url_for("index"))
    bl = load_blacklist()
    if item in bl:
        flash(f"'{item}' already in blacklist.")
    else:
        bl.append(item)
        save_blacklist(bl)
        flash(f"Added: {item}")
    return redirect(url_for("index"))

@app.route("/remove", methods=["POST"])
def remove():
    item = request.form.get("item", "").strip()
    bl = load_blacklist()
    if item in bl:
        bl = [x for x in bl if x != item]
        save_blacklist(bl)
        flash(f"Removed: {item}")
    else:
        flash(f"Not found: {item}")
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=42000, debug=True)