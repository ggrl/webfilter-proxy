from flask import Flask, request, redirect, url_for, render_template_string, flash
import json
import os

app = Flask(__name__)
app.secret_key = "dev-secret"  # replace with a secure key if exposing publicly

BLACKLIST_FILE = "data/blacklist.json"

def load_blacklist():
    if not os.path.exists(BLACKLIST_FILE):
        return []
    with open(BLACKLIST_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_blacklist(lst):
    with open(BLACKLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(lst, f, indent=2)

# Simple inline template so app is only one file
TEMPLATE = """
<!doctype html>
<html>
<head><meta charset="utf-8"><title>proxy settings</title>
<style>
body { font-family: system-ui, Arial; max-width: 800px; margin: 2rem; }
input[type=text]{ width: 60%; padding: 0.4rem }
button{ padding: 0.4rem 0.6rem }
li { margin: 0.4rem 0 }
.small { color: #666; font-size:0.9rem }
</style>
</head>
<body>
  <h1>proxy settings</h1>
  {% with messages = get_flashed_messages() %}
    {% if messages %}
      <ul>
      {% for m in messages %}
        <li style="color:green">{{ m }}</li>
      {% endfor %}
      </ul>
    {% endif %}
  {% endwith %}

  <form method="post" action="{{ url_for('add') }}">
    <input name="item" placeholder="enter website..." required>
    <button type="submit">Add</button>
  </form>

  <h2>Current blacklist ({{ blacklist|length }})</h2>
  <ul>
  {% for item in blacklist %}
    <li>
      <strong>{{ item }}</strong>
      <form method="post" action="{{ url_for('remove') }}" style="display:inline">
        <input type="hidden" name="item" value="{{ item }}">
        <button type="submit">Remove</button>
      </form>
    </li>
  {% else %}
    <li class="small">(empty)</li>
  {% endfor %}
  </ul>

 
</body>
</html>
"""

@app.route("/")
def index():
    bl = load_blacklist()
    return render_template_string(TEMPLATE, blacklist=bl)

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
    # Only listen on localhost by default — safer during development
    app.run(host="127.0.0.1", port=42000, debug=True)