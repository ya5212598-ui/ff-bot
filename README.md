# 🔥 Free Fire Auto-Like Telegram Bot (v3)

Ekta Telegram bot je Free Fire player der LIKE pathay — **manual** (`/like`) ebong
**automatic protidin** (auto-like scheduler) duivabei.

> 🆕 **v3 te notun:** ekta **DEFAULT public like API already boshano ache**. Tai
> tumi shudhu **`BOT_TOKEN`** boshiye chalalei bot like try korbe — alada kore
> API boshanor dorkar nai (jotokkhon default API ta beche thake)।

---

## ⚠️ IMPORTANT — Garena er Official Like API NAI (porte hobe)

> **Garena / Free Fire kono official "send like" API public kore na.**
> Internet e ja ja pawa jay shob-i **third-party / community-hosted** free API.
> Eder ekta boro somossya:
>
> ### 🚨 Free / public API gula GUARANTEE NAI
> - Eder onek-i **maje maje bondho (down)** hoye jay, host expire kore, ba
>   **rate-limit** kore (din e ekbar-duibar er beshi like ney na).
> - Tai aj kaj korle kal nao korte pare.
> - **Bondho hole tomake `LIKE_API_URL` palte hobe** — ekta notun kaj kora
>   endpoint khuje niye `.env` e boshao (niche dekhano ache kibhabe)।
>
> Mane: ei bot nije like banay na; eta ekta public/your like API ke ekta sundor
> Telegram interface + daily scheduler diye wrap kore.

---

## 🔧 v3 te like API kibhabe kaj kore

Bot er moddhe `bot.py` te ekta **default endpoint list** ache
(`DEFAULT_LIKE_ENDPOINTS`)। Logic:

1. **Jodi tumi `.env` te `LIKE_API_URL` dao** → bot shudhu **tomar** API use korbe.
2. **Na dile** → bot default list er **protita endpoint try kore** — ekta down
   thakle **automatic porer ta** try kore (fallback)। Prothom je ta kaj kore
   seta theke **before → added → after** dekhay।
3. **Shob endpoint down hole** → bot poriskar kore bole *"sob API down/rate-limited,
   .env e nijer LIKE_API_URL boshao"* + kon gula fail korlo tar list।

> 💡 Default endpoint gula community project (jemon `jinix6/free-ff-api` style)
> theke neya। Eder beche thakar **kono guarantee nai** — eta normal। Bondho hole
> niche **"Notun API kibhabe boshabo"** dekho।

---

## ✨ Features

| Command | Ki kore |
|---|---|
| `/like bd <uid>` | Ekbar manual like pathay |
| `/autolike bd <uid>` | UID ke daily auto-like er jonno register kore (+ sathe sathe ekbar like dey) |
| `/stop <uid>` | Oi UID er auto-like bondho kore |
| `/list` | Tomar register kora sob UID dekhay |
| `/start` / `/help` | Help message |

- ⏰ **Daily scheduler** (APScheduler): protidin nirdishto somoy e sob register kora UID ke `DAILY_LIKES` like pathay.
- 💾 **Persistent storage** (SQLite `likebot.db`): restart hole o data thake.
- 🔁 **Multi-endpoint fallback**: ekta API down hole automatic onnota try kore.
- 🔧 **Fully configurable** via environment variables.

---

## 🚀 Quick Start (shudhu token diye)

```bash
# 1) Ei folder e dhoko
cd freefire-like-bot-v3

# 2) Dependencies install
pip install -r requirements.txt

# 3) .env banao — shudhu BOT_TOKEN boshao
cp .env.example .env
# .env edit koro: BOT_TOKEN=<BotFather theke pawa token>
# LIKE_API_URL khali rakhle default public API try korbe

# 4) Run
python run.py
```

Telegram e tomar bot e giye `/start` dao → tarpor `/like bd 123456789` try koro.

---

## 🔑 Environment Variables

| Variable | Required | Default | Mane |
|---|---|---|---|
| `BOT_TOKEN` | ✅ | — | BotFather (https://t.me/BotFather) theke pawa token |
| `LIKE_API_URL` | ❌ | (empty → default public API) | Tomar nijer like API. Khali rakhle bot er built-in default list use kore |
| `LIKE_API_KEY` | ❌ | (empty) | API key, jodi tomar API chai |
| `DAILY_LIKES` | ❌ | `200` | Protidin koto like (e.g. `300`) |
| `REGION` | ❌ | `bd` | Default region |
| `SCHEDULE_HOUR` | ❌ | `0` | Daily job er ghonta (24h) |
| `SCHEDULE_MINUTE` | ❌ | `5` | Daily job er minute |
| `TZ` | ❌ | `UTC` | Timezone, e.g. `Asia/Dhaka` |
| `HTTP_TIMEOUT` | ❌ | `30` | API call timeout (sec) |
| `DB_PATH` | ❌ | `likebot.db` | SQLite file path |

---

## 🔌 Notun / nijer API kibhabe boshabo (jokhon default ta down)

Default public API bondho hole, ekta kaj kora endpoint khuje niye `.env` e boshao:

```env
LIKE_API_URL=https://your-working-host/like
LIKE_API_KEY=        # jodi lage
```

Bot ei GET request pathay:

```
GET <LIKE_API_URL>?uid=<uid>&region=bd&key=<LIKE_API_KEY>
Header: Authorization: Bearer <LIKE_API_KEY>   (jodi key dao)
```

Ar JSON response theke ei field gula **auto-detect** kore (boro list, nested o dhore):

- **before:** `likes_before` / `before` / `PreLikes` / `LikesbeforeCommand` …
- **added:** `likes_added` / `added` / `LikesGiven` / `LikesGivenByAPI` …
- **after:** `likes_after` / `after` / `AfterLikes` / `likes` …

> Tomar API onno field name ba onno request style use korle, `bot.py` er
> `call_like_api()` / `_parse_like_response()` adjust kore nio — comment kora ache।

### Notun endpoint kothay khujbo?
GitHub e search koro: **"freefire like api"**, **"free fire free like api"**.
Onek community repo (jemon `jinix6/free-ff-api`) tader live host + `/api/v1/...`
endpoint dey। Je host beche ache, seta `LIKE_API_URL` e boshao।

---

## ☁️ 24/7 Hosting

Bot ke 24/7 cholanor jonno ekta always-on host lagbe. 3 ta option:

### Option A — Railway (sobcheye sohoj)
1. https://railway.app e account khulo.
2. **New Project → Deploy from GitHub repo** (ei folder ta ekta GitHub repo te push koro).
3. Railway auto `requirements.txt` detect korbe. `Procfile` already deya ache (`worker: python run.py`).
4. **Variables** tab e env var add koro (`BOT_TOKEN` minimum, sathe `DAILY_LIKES`, `TZ=Asia/Dhaka`, etc.).
5. Deploy → bot 24/7 cholbe. (Free tier e usage limit ache.)

### Option B — Render
1. https://render.com → **New → Background Worker**.
2. Repo connect koro.
3. **Build Command:** `pip install -r requirements.txt`
4. **Start Command:** `python run.py`
5. **Environment** e env var gula add koro.
6. Create → done. (Note: Render free **web** service ghumiye jay; tai **Background Worker** use koro.)

### Option C — VPS (DigitalOcean / AWS / Contabo / nijer Linux server)
```bash
sudo apt update && sudo apt install -y python3-venv git
git clone <tomar-repo> && cd freefire-like-bot-v3
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env && nano .env        # BOT_TOKEN boshao

# systemd diye always-on service banao:
sudo tee /etc/systemd/system/ffbot.service > /dev/null <<'EOF'
[Unit]
Description=Free Fire Like Bot
After=network.target

[Service]
WorkingDirectory=/root/freefire-like-bot-v3
ExecStart=/root/freefire-like-bot-v3/venv/bin/python run.py
Restart=always
EnvironmentFile=/root/freefire-like-bot-v3/.env

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now ffbot
sudo systemctl status ffbot      # cholche kina dekho
journalctl -u ffbot -f           # live log
```

> 💡 Daily scheduler bot er process er bhitore chole. Tai bot 24/7 online thakle
> protidin job tik moto cholbe. Bot off thakle scheduler o off.

---

## 📁 Project Structure

```
freefire-like-bot-v3/
├── bot.py              # Main bot logic (commands + scheduler + multi-endpoint API caller + DB)
├── run.py              # Entry point je .env load kore (python run.py)
├── requirements.txt    # Dependencies
├── .env.example        # Env var template (copy kore .env banao)
├── Procfile            # Railway/Render er jonno
└── README.md           # Ei file
```

---

## ❓ FAQ / Troubleshooting

- **Bot start hocche na, "BOT_TOKEN set kora nai"** → `.env` e `BOT_TOKEN` bosao.
- **"Kono like API kaj korlo na (sob down/rate-limited)"** → default public API gula ekhon down/rate-limited. Ekta notun kaj kora endpoint khuje `.env` e `LIKE_API_URL` boshao.
- **Like fail / 0 added** → oi API `bd` region support kore kina, ar response format alada kina check koro. Alada hole `call_like_api()` adjust koro.
- **Daily job cholche na** → bot ki 24/7 online? `TZ` ar `SCHEDULE_HOUR/MINUTE` thik kina dekho.

---

## 📜 Disclaimer

Ei bot purely **educational / personal use** er jonno. Free Fire / Garena er
official kono like API **nai**; third-party / public service use korle oi service
er terms ar Garena er Terms of Service mene chola tomar nijer responsibility.
Free public API bondho ba rate-limit korle setar control amader hate nai। Misuse
hole author dayi noy.
