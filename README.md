# SeenIt

A Discord bot that removes duplicate links and images. When someone posts something that was already posted, the bot deletes the message and replies with a pointer to the original.

## Features

- **Duplicate links**: URLs are normalized before comparing (tracking params stripped, `www.`/`m.` and mirror hosts like `fxtwitter.com` mapped to the canonical host, fragments and trailing slashes dropped).
- **Redirect resolving**: share and short links (Facebook `/share/`, `fb.watch`, TikTok, Reddit `/s/`, `bit.ly`, `t.co`, etc.) are followed to the real URL using `curl_cffi` with a Chrome TLS fingerprint.
- **Duplicate images**: attachments are compared with perceptual hashing (pHash), so re-compressed or resized copies still match.
- **Embed fixer support**: can wait for an embed fixer bot to repost a link, then check the fixer's link instead.
- **Custom removal messages**: add messages with a slash command; one is picked at random each time.
- **Scope**: match across the whole server, or only within the same channel.

## Requirements

- Python 3.10+
- A Discord bot token with **Message Content Intent** enabled (Developer Portal, Bot tab, Privileged Gateway Intents)
- Bot permissions: View Channel, Read Message History, Send Messages, **Manage Messages**
- Invite the bot with the `bot` and `applications.commands` scopes

## Local development

For running and testing the bot on your own machine. For deployment, see [Docker](#docker).

```bash
git clone https://github.com/<you>/seen-it
cd seen-it
python -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env   # then fill it in
python src/main.py
```

The SQLite database is created and migrated automatically on startup.

## Configuration

Set these in `.env`:

| Variable                     | Required | Description                                                                                             |
| ---------------------------- | -------- | ------------------------------------------------------------------------------------------------------- |
| `BOT_TOKEN`                  | yes      | Discord bot token                                                                                       |
| `USING_EMBED_FIXER`          | yes      | `True` if an embed fixer bot is in the server, otherwise `False`                                        |
| `CHECKED_BY_CHANNEL`         | no       | `true` to only match duplicates posted in the same channel. Default: whole server                       |
| `IMAGE_COMPARISON_THRESHOLD` | no       | Max pHash bit difference (out of 64) to count two images as duplicates. Lower is stricter. Default: `5` |
| `SHAME_DURATION`             | no       | Seconds before the bot's removal notice deletes itself. If unset, it stays                              |
| `DATABASE_PATH`              | no       | SQLite file path. Default: `src/database/seenit.db`                                                     |

Example:

```env
BOT_TOKEN=your-token-here
USING_EMBED_FIXER=False
CHECKED_BY_CHANNEL=true
SHAME_DURATION=90
```

## Embed fixer mode

With `USING_EMBED_FIXER=True`:

- Messages from the embed fixer are processed using the link buttons on its message.
- Messages from users wait 7 seconds. If the embed fixer deleted the original in that time, the bot ignores it and checks the fixer's repost instead.

## Custom messages

Add a removal message (requires Manage Server):

```
/addmessage template:@author.mention already posted by @original_author at @created_at, see @original_message
```

Manage them with:

- `/listmessages` shows every custom message with its ID.
- `/removemessage id:<id>` deletes one.

If a server has several, one is chosen at random. With none, a default message is used.

| Placeholder         | Replaced with                                               |
| ------------------- | ----------------------------------------------------------- |
| `@author.mention`   | Mention of the person who just posted                       |
| `@author.name`      | Display name of that person                                 |
| `@original_author`  | Mention of the original poster                              |
| `@created_at`       | Time of the original post (shown in each viewer's timezone) |
| `@channel`          | Channel of the original post                                |
| `@original_message` | Jump link(s) to the original message(s)                     |
| `@guild`            | Server name                                                 |

Unknown `@words` (like `@everyone`) are left as written.

## Docker

This is the recommended way to run the bot in production.

```dockerfile
FROM python:3.14-slim
WORKDIR /app
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir -e .
CMD ["python", "src/main.py"]
```

Compose service:

```yaml
services:
  seenit:
    container_name: seenit
    build: .
    restart: unless-stopped
    env_file: .env
    environment:
      - DATABASE_PATH=/app/data/seenit.db
    volumes:
      - ./data:/app/data
```

Keep the database on a bind mount so rebuilds don't wipe saved links. After pulling new code, rebuild with `docker compose up -d --build`.

## Database migrations

Migrations live in the `MIGRATIONS` list in `queries.py`, tracked with `PRAGMA user_version`. To change the schema, append a new entry. Never edit or reorder existing ones.

## Limitations

- Image matching misses crops, flips, rotations and heavy edits. Low-detail images and meme templates can cause false positives.
- Only image attachments are hashed, not image links or videos. GIFs hash their first frame only.
- Facebook sometimes serves a login wall to server IPs. Those links fall back to the raw URL and won't dedupe.
- The same Facebook post can have both a numeric and a `pfbid...` ID, which are not unified.
- Messages posted before a feature was added are not checked against it.
- Without **Manage Messages**, the bot cannot delete duplicates.
