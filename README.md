# 🤖 Telegram Auto Join Request Bot

A premium, high-performance Telegram Auto Join Request Acceptor & Approver bot with a built-in verification system ("I'm Not a Robot"), Force Subscription engine, multi-language support (English, Hindi, Hinglish, Urdu), speed-controlled bulk approval queue, and a powerful owner panel.

Built with Python and the high-performance MTProto library `pyrofork` and backed by **MongoDB**. Ready for **Heroku** and **GitHub** deployment.

---

## ✨ Features

- **Premium Bold Styling**: Bold unicode formatting ("𝗘𝗫𝗔𝗠𝗣𝗟𝗘") applied dynamically across latin texts, headings, menus, reports, and inline buttons.
- **Multilingual Support**: Supports 🇬🇧 English, 🇮🇳 Hindi, 🇮🇳 Hinglish, and 🇵🇰 Urdu.
- **Force Subscription (FSub)**: Global ON/OFF control, supports unlimited public/private channels/groups, and checks/lists only remaining required chats.
- **Hidden Verification**: Global ON/OFF control for "I'm Not a Robot" verification that triggers a verification payload to register users in the DB before approving requests.
- **High-Speed Bulk Approval**: Safe queue processing supporting pause, resume, and stop controls with automatic flood wait protection.
- **Automatic Connection Detection**: Sends configuration reports directly to the user who installs the bot as admin.
- **Comprehensive Owner Panel**: Controls global parameters, broadcasting, user banning, fsub chat setups, and real-time statistics.

---

## 🛠️ Heroku Deployment Guide

Deploying this bot to Heroku requires configuring only three main variables.

### Step 1: Create a MongoDB Database
Get a free cluster URI from [MongoDB Atlas](https://www.mongodb.com/cloud/atlas).
- Create a database user.
- Copy your connection string (looks like `mongodb+srv://<username>:<password>@cluster.xxxx.mongodb.net/database_name`).

### Step 2: Deploy to Heroku
You can deploy using the Heroku Dashboard:
1. Create a new Heroku App.
2. In **Settings** -> **Reveal Config Vars**, add:
   - `BOT_TOKEN`: Your Telegram Bot Token from `@BotFather`.
   - `OWNER_ID`: Your numeric Telegram user ID (the main owner).
   - `MONGO_DB_URI`: Your MongoDB connection string.
   - Do not set `SESSION_STRING`. The bot now authenticates from the current `BOT_TOKEN` on every boot so stale Telegram sessions cannot swallow `/start` and `/admin` updates.
3. Link your GitHub repository in the **Deploy** tab.
4. Deploy the main branch.
5. In **Resources** tab, disable the web dyno and **enable the worker dyno** (`python bot.py`).

*Note: A default, public pair of Telegram API ID/Hash credentials is built into the code so you do not need to configure them unless you choose to override them.*

### If `/start` or `/admin` does not respond

1. Confirm the Heroku **worker** dyno is enabled and there is no web dyno running this bot.
2. Confirm `BOT_TOKEN`, `OWNER_ID`, and `MONGO_DB_URI` are set in Heroku config vars.
3. Remove any old `SESSION_STRING` config var if it exists.
4. Restart the worker dyno after changing config vars.

---

## 💻 Local Setup & Development

### 1. Set Active Workspace
Open your IDE or terminal and set your active workspace to:
`C:\Users\HP\.gemini\antigravity-ide\scratch\telegram-join-request-bot`

### 2. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Open `.env` and fill in:
- `BOT_TOKEN`
- `OWNER_ID`
- `MONGO_DB_URI`

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Bot
```bash
python bot.py
```

### 5. Run Unit Tests
To verify local code functionality:
```bash
python test_bot.py
```
