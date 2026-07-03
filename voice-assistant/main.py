"""
Telefon-Sprachassistent (Twilio + OpenAI Realtime API).

Angepasst fuer den Betrieb auf Replit, basierend auf der urspruenglichen
PythonAnywhere-Version ("telefonikunchatgptplusscio.py"). Wichtigste Aenderungen:

- Kein ngrok mehr noetig: Replit stellt bereits eine oeffentliche HTTPS/WSS-Adresse
  bereit, unter der Twilio den Server erreichen kann.
- Alle Routen liegen unter dem Praefix BASE_PATH ("/voice"), weil der gemeinsame
  Reverse-Proxy Anfragen anhand des Pfades an diesen Dienst weiterleitet.
- Die scio.txt-Aktualisierung ("scio1.py") laeuft als Hintergrund-Task in diesem
  Prozess, statt als separates Cron-Skript.
- Zugangsdaten (OPENAI_API_KEY, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN) kommen aus
  den Replit Secrets (Umgebungsvariablen), nicht aus einer .env-Datei.
"""

import os
import json
import base64
import asyncio
from datetime import datetime, timedelta
from pathlib import Path

import aiofiles
import feedparser
import requests
import websockets
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.websockets import WebSocketDisconnect
from twilio.twiml.voice_response import VoiceResponse, Connect
from twilio.rest import Client as TwilioClient

# ---------------------------------------------------------------------------
# Konfiguration
# ---------------------------------------------------------------------------

BASE_PATH = "/voice"

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY fehlt. Bitte in den Replit Secrets setzen.")

TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")

PORT = int(os.environ.get("PORT", 8000))
TEMPERATURE = float(os.environ.get("TEMPERATURE", 0.8))
VOICE = os.environ.get("REALTIME_VOICE", "marin")

DATA_DIR = Path(__file__).parent
SCIO_FILE = DATA_DIR / "scio.txt"

# Oefentliaj RSS-fontoj kun mondaj novajhoj (anstatau la mortinta Gist-URL de la
# originala skripto). Neniu API-shlosilo bezonata.
NEWS_FEED_URLS = [
    "http://feeds.bbci.co.uk/news/world/rss.xml",
    "http://feeds.bbci.co.uk/news/world/europe/rss.xml",
]
NEWS_ITEMS_PER_FEED = 6

# Vetero por kelkaj Europaj urboj, per la senpaga wttr.in-servo (neniu shlosilo bezonata).
WEATHER_CITIES = ["Berlin", "Paris", "London", "Warsaw"]

SCIO_REFRESH_MINUTES = int(os.environ.get("SCIO_REFRESH_MINUTES", 30))

LOG_EVENT_TYPES = [
    "error", "response.content.done", "rate_limits.updated",
    "response.done", "input_audio_buffer.committed",
    "input_audio_buffer.speech_stopped", "input_audio_buffer.speech_started",
    "session.created", "session.updated",
]
SHOW_TIMING_MATH = False

twilio_client = None
if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
    twilio_client = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

app = FastAPI()

SCIO_CACHE = None
SCIO_LAST_UPDATED = None


# ---------------------------------------------------------------------------
# scio.txt: Hintergrundwissen, das periodisch aktualisiert wird
# ---------------------------------------------------------------------------

def fetch_news_section() -> str:
    """Holt aktuelle Weltnachrichten per RSS (BBC World/Europe), ohne Duplikate."""
    seen_titles = set()
    lines = []
    headers = {"User-Agent": "Mozilla/5.0 (compatible; ReplitVoiceAssistant/1.0)"}
    for url in NEWS_FEED_URLS:
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            feed = feedparser.parse(response.content)
            for entry in feed.entries[:NEWS_ITEMS_PER_FEED]:
                title = entry.get("title", "").strip()
                summary = entry.get("summary", "").strip()
                if title and title not in seen_titles:
                    seen_titles.add(title)
                    lines.append(f"- {title}" + (f": {summary}" if summary else ""))
        except Exception as e:
            print(f"[scio] Fehler beim Abrufen des Feeds {url}: {e}")
    if not lines:
        return ""
    return "NOVAĴOJ:\n" + "\n".join(lines)


def fetch_weather_section() -> str:
    """Holt aktuellen Wetterbericht fuer ein paar europaeische Staedte (wttr.in, kein API-Key noetig)."""
    lines = []
    for city in WEATHER_CITIES:
        try:
            response = requests.get(f"https://wttr.in/{city}", params={"format": "3"}, timeout=10)
            response.raise_for_status()
            text = response.text.strip()
            if text:
                lines.append(f"- {text}")
        except Exception as e:
            print(f"[scio] Fehler beim Abrufen des Wetters fuer {city}: {e}")
    if not lines:
        return ""
    return "VETERO EN EŬROPO:\n" + "\n".join(lines)


def fetch_scio_data() -> str | None:
    """Baut den Hintergrundwissen-Text aus Nachrichten- und Wetterdaten zusammen."""
    sections = [s for s in (fetch_news_section(), fetch_weather_section()) if s]
    if not sections:
        return None
    return "\n\n".join(sections)


async def refresh_scio_file():
    """Schreibt die aktuellen Zusatzdaten in scio.txt (mit Zeitstempel)."""
    content = fetch_scio_data()
    if content is None:
        return
    timestamp = datetime.now().isoformat()
    formatted = f"# Aktualisiert am: {timestamp}\n\n{content}"
    async with aiofiles.open(SCIO_FILE, "w", encoding="utf-8") as f:
        await f.write(formatted)
    print(f"[scio] scio.txt aktualisiert ({len(content)} Zeichen)")


async def scio_refresh_loop():
    """Aktualisiert scio.txt regelmaessig im Hintergrund."""
    while True:
        try:
            await refresh_scio_file()
        except Exception as e:
            print(f"[scio] Hintergrund-Update fehlgeschlagen: {e}")
        await asyncio.sleep(SCIO_REFRESH_MINUTES * 60)


async def get_scio_data():
    """Liest scio.txt und cached das Ergebnis fuer 5 Minuten."""
    global SCIO_CACHE, SCIO_LAST_UPDATED

    if SCIO_LAST_UPDATED and datetime.now() - SCIO_LAST_UPDATED < timedelta(minutes=5):
        return SCIO_CACHE

    try:
        async with aiofiles.open(SCIO_FILE, "r", encoding="utf-8") as f:
            content = await f.read()
        if not content.strip():
            return None
        SCIO_CACHE = {
            "content": content,
            "last_updated": datetime.now().isoformat(),
            "size_chars": len(content),
            "size_lines": len(content.split("\n")),
        }
        SCIO_LAST_UPDATED = datetime.now()
        return SCIO_CACHE
    except FileNotFoundError:
        return None
    except Exception as e:
        print(f"[scio] Fehler beim Lesen von scio.txt: {e}")
        return None


async def get_system_message() -> str:
    """Baut die Systemnachricht fuer die KI, inkl. optionaler Zusatzdaten."""
    base_message = (
        "Vi estas ĝentila kaj helpopreta asistanto, kiu treege bone komprenas kaj parolas "
        "precipe Esperanton. Respondu klare, nature kaj per mallongaj, facile parolindaj frazoj."
    )

    scio_data = await get_scio_data()
    if not scio_data:
        return base_message

    content = scio_data["content"]
    if len(content) > 2500:
        content = content[:2500] + "... [plia enhavo tranĉita]"

    return base_message + (
        f"\n\nAKTUALAJ DONITAĴOJ (ĝisdatigita: {scio_data['last_updated']}):\n"
        f"{content}\n\n"
        "Uzu la suprajn donitaĵojn nur kiam oni demandas pri aktualaj eventoj aŭ novaĵoj. "
        "Se vi ne certas pri io, diru tion honeste anstataŭ inventi informojn."
    )


# ---------------------------------------------------------------------------
# HTTP-Routen (alle unter BASE_PATH, weil der Proxy den Pfad nicht umschreibt)
# ---------------------------------------------------------------------------

@app.get(BASE_PATH + "/", response_class=JSONResponse)
async def index_page():
    return {"message": "Telefon-Sprachassistent laeuft."}


@app.get(BASE_PATH + "/health")
async def health_check():
    scio_data = await get_scio_data()
    return JSONResponse({
        "status": "healthy",
        "scio_data_available": bool(scio_data),
        "last_updated": scio_data.get("last_updated") if scio_data else None,
    })


@app.get(BASE_PATH + "/scio-data")
async def scio_data_endpoint():
    scio_data = await get_scio_data()
    if scio_data:
        return JSONResponse(scio_data)
    return JSONResponse({"error": "Keine Zusatzdaten verfuegbar"}, status_code=404)


@app.api_route(BASE_PATH + "/incoming-call", methods=["GET", "POST"])
async def handle_incoming_call(request: Request):
    """Diese URL bei Twilio als Webhook fuer eingehende Anrufe eintragen."""
    response = VoiceResponse()
    response.say(
        "Saluton! Ni konektas vin kun virtuala asistanto kun voĉo kreita per "
        "artefarita intelekto kaj funkciigata per Twilio kombine kun OpenAI.",
        voice="Polly.Ewa",
    )
    response.pause(length=1)
    response.say(
        "Bonvolu komenci paroli.",
        voice="Polly.Ewa",
    )

    host = request.url.hostname
    connect = Connect()
    connect.stream(url=f"wss://{host}{BASE_PATH}/media-stream")
    response.append(connect)
    return HTMLResponse(content=str(response), media_type="application/xml")


@app.websocket(BASE_PATH + "/media-stream")
async def handle_media_stream(websocket: WebSocket):
    """Verbindet den Twilio-Audiostream in Echtzeit mit der OpenAI Realtime API."""
    print("Anrufer verbunden.")
    await websocket.accept()

    current_system_message = await get_system_message()

    async with websockets.connect(
        f"wss://api.openai.com/v1/realtime?model=gpt-realtime&temperature={TEMPERATURE}&voice={VOICE}",
        additional_headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
    ) as openai_ws:
        await initialize_session(openai_ws, current_system_message)

        stream_sid = None
        latest_media_timestamp = 0
        last_assistant_item = None
        mark_queue = []
        response_start_timestamp_twilio = None

        async def receive_from_twilio():
            nonlocal stream_sid, latest_media_timestamp
            try:
                async for message in websocket.iter_text():
                    data = json.loads(message)
                    if data["event"] == "media" and openai_ws.state.name == "OPEN":
                        latest_media_timestamp = int(data["media"]["timestamp"])
                        await openai_ws.send(json.dumps({
                            "type": "input_audio_buffer.append",
                            "audio": data["media"]["payload"],
                        }))
                    elif data["event"] == "start":
                        stream_sid = data["start"]["streamSid"]
                        print(f"Stream gestartet: {stream_sid}")
                        latest_media_timestamp = 0
                    elif data["event"] == "mark":
                        if mark_queue:
                            mark_queue.pop(0)
            except WebSocketDisconnect:
                print("Anrufer hat aufgelegt.")
                if openai_ws.state.name == "OPEN":
                    await openai_ws.close()

        async def send_to_twilio():
            nonlocal stream_sid, last_assistant_item, response_start_timestamp_twilio
            try:
                async for openai_message in openai_ws:
                    response = json.loads(openai_message)
                    if response["type"] in LOG_EVENT_TYPES:
                        print(f"Event: {response['type']}")

                    if response.get("type") == "response.output_audio.delta" and "delta" in response:
                        audio_payload = base64.b64encode(base64.b64decode(response["delta"])).decode("utf-8")
                        await websocket.send_json({
                            "event": "media",
                            "streamSid": stream_sid,
                            "media": {"payload": audio_payload},
                        })

                        if response.get("item_id") and response["item_id"] != last_assistant_item:
                            response_start_timestamp_twilio = latest_media_timestamp
                            last_assistant_item = response["item_id"]

                        await send_mark(websocket, stream_sid)

                    if response.get("type") == "input_audio_buffer.speech_started":
                        if last_assistant_item:
                            await handle_speech_started_event()
            except Exception as e:
                print(f"Fehler in send_to_twilio: {e}")

        async def handle_speech_started_event():
            nonlocal response_start_timestamp_twilio, last_assistant_item
            if mark_queue and response_start_timestamp_twilio is not None:
                elapsed_time = latest_media_timestamp - response_start_timestamp_twilio
                if last_assistant_item:
                    await openai_ws.send(json.dumps({
                        "type": "conversation.item.truncate",
                        "item_id": last_assistant_item,
                        "content_index": 0,
                        "audio_end_ms": elapsed_time,
                    }))
                await websocket.send_json({"event": "clear", "streamSid": stream_sid})
                mark_queue.clear()
                last_assistant_item = None
                response_start_timestamp_twilio = None

        async def send_mark(connection, stream_sid_local):
            if stream_sid_local:
                await connection.send_json({
                    "event": "mark",
                    "streamSid": stream_sid_local,
                    "mark": {"name": "responsePart"},
                })
                mark_queue.append("responsePart")

        await asyncio.gather(receive_from_twilio(), send_to_twilio())


async def initialize_session(openai_ws, system_message: str):
    session_update = {
        "type": "session.update",
        "session": {
            "type": "realtime",
            "model": "gpt-realtime",
            "output_modalities": ["audio"],
            "audio": {
                "input": {
                    "format": {"type": "audio/pcmu"},
                    "turn_detection": {"type": "server_vad"},
                },
                "output": {"format": {"type": "audio/pcmu"}},
            },
            "instructions": system_message,
        },
    }
    await openai_ws.send(json.dumps(session_update))


@app.on_event("startup")
async def on_startup():
    asyncio.create_task(scio_refresh_loop())


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
