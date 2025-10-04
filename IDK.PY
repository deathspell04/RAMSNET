import os
import base64
from datetime import datetime
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

def send_task_single(bot_id, task_type, command):
    # llama a la implementación existente
    ok, msg = _real_send_task_single(bot_id, task_type, command)  # sustituye por el nombre real

    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    safe_bot = str(bot_id).replace(os.sep, "_")
    txt_name = f"{timestamp}_{safe_bot}_{task_type}.txt"
    txt_path = os.path.join(RESULTS_DIR, txt_name)

    try:
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(f"bot_id: {bot_id}\n")
            f.write(f"type: {task_type}\n")
            f.write(f"command: {command}\n")
            f.write("msg:\n")
            f.write(repr(msg))
        logger.debug("Wrote result metadata to %s", txt_path)
    except Exception as e:
        logger.exception("Error writing txt result: %s", e)

    # Si msg es dict y contiene 'screenshot_b64', guárdala como PNG
    try:
        if isinstance(msg, dict):
            b64 = msg.get("screenshot_b64") or msg.get("screenshot")
            if b64:
                # limpiar prefijo data: si lo tiene
                if isinstance(b64, str) and b64.startswith("data:"):
                    b64 = b64.split(",", 1)[1]
                img_path = os.path.join(RESULTS_DIR, f"{timestamp}_{safe_bot}.png")
                with open(img_path, "wb") as imgf:
                    imgf.write(base64.b64decode(b64))
                logger.debug("Wrote screenshot to %s", img_path)
    except Exception as e:
        logger.exception("Error saving screenshot: %s", e)

    return ok, msg