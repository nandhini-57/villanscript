# ☠ VillanScript — Full Stack Edition

A villain-themed text rewriter. 

---

## 🏗 Architecture

```
villanscript/
├── app.py              ← Flask backend + REST API + villain engine
├── static/
│   └── index.html      ← Full frontend (7 pages, all features)
├── villanscript.db     ← SQLite database (auto-created on first run)
└── README.md
```

| Layer      | Technology               |
|------------|--------------------------|
| Frontend   | HTML5 + CSS3 + Vanilla JS |
| Backend    | Python + Flask           |
| Database   | SQLite (via sqlite3)     |
| API Style  | REST (JSON)              |

---

## 🚀 Setup & Run

**Requirements:** Python 3.8+ and Flask

```bash
# Install Flask (if not already installed)
pip install flask

# Run the server
python app.py
```

## 📄 Pages

| Page      | Description                                      |
|-----------|--------------------------------------------------|
| 🏠 Home    | Landing page with 3 villain mode cards           |
| 😈 Menacing | Cold, calculating villain rewriter             |
| 🎭 Dramatic | Theatrical, explosive villain rewriter         |
| 🌑 Unhinged | Chaotic, manic villain rewriter               |
| 📜 History  | Full archive of all rewrites with search/filter|
| ❤️ Favs    | Bookmarked villain lines                        |
| 📊 Stats   | XP, villain rank, mode usage, top intents       |

---

## 🔌 REST API Endpoints

| Method | Endpoint                  | Description                    |
|--------|---------------------------|--------------------------------|
| POST   | `/api/rewrite`            | Generate villain line, save to DB |
| GET    | `/api/history`            | Get last 60 rewrites           |
| GET    | `/api/favourites`         | Get all favourited entries     |
| PATCH  | `/api/favourite/:id`      | Toggle favourite on an entry   |
| DELETE | `/api/rewrite/:id`        | Delete a single entry          |
| DELETE | `/api/history`            | Clear all non-favourited entries |
| GET    | `/api/stats`              | Full stats + rank + XP         |
| GET    | `/api/random_villain_line`| Random villain line (for fun)  |

---

## ✨ Features

- 3 villain modes: Menacing, Dramatic, Unhinged
- Page navigation with unique themes per mode
- 30+ intent detection categories (regex-based NLP)
- 360+ hand-crafted villain responses
- Typewriter animation with punctuation-aware speed
- Animated UI (skull bob, fire glow, screen shake on Unhinged)
- Scanlines overlay, per-mode color themes
- Ctrl+Enter shortcut

---

## 🧠 Villain Rank System

| XP     | Rank                |
|--------|---------------------|
| 0      | Pathetic Minion     |
| 50     | Scheming Lackey     |
| 150    | Dark Apprentice     |
| 300    | Shadow Commander    |
| 500    | Warlord of Chaos    |
| 800    | Dread Sovereign     |
| 1200   | Eternal Overlord    |
| 2000   | The Dark Lord       |



