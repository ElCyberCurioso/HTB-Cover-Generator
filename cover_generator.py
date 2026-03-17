#!/usr/bin/env python3
"""
HTB Machine Cover Generator
Genera una portada visual con la información de una máquina de HackTheBox.

Uso:
    python3 htb_cover.py <nombre_maquina> --token <tu_api_token>
    python3 htb_cover.py <nombre_maquina> --token <tu_api_token> --output portada.png

Obtén tu API token en: https://app.hackthebox.com/profile/settings -> API Key
"""

import argparse
import io
import math
import os
import sys
from datetime import datetime

import requests
from PIL import Image, ImageDraw, ImageFilter, ImageFont

# ─── Configuración ────────────────────────────────────────────────────────────

HTB_API_BASE      = "https://labs.hackthebox.com/api/v4"
HTB_AVATAR_S3     = "https://htb-mp-prod-public-storage.s3.eu-central-1.amazonaws.com/avatars/{filename}"
HTB_AVATAR_WWW    = "https://www.hackthebox.com"   # fallback

CANVAS_W, CANVAS_H = 1200, 675   # 16:9

# Paleta de colores HTB
COLOR_BG_TOP    = (10,  14,  20)
COLOR_BG_BOT    = (15,  22,  35)
COLOR_GREEN     = (159, 239, 0)   # verde HTB
COLOR_GREEN_DIM = (80,  120,  0)
COLOR_WHITE     = (240, 240, 240)
COLOR_GREY      = (130, 140, 155)
COLOR_DARK_CARD = (20,  30,  45)
COLOR_BORDER    = (30,  50,  70)

# Colores de dificultad
DIFFICULTY_COLORS = {
    "Easy":     (0,   200,  80),
    "Medium":   (255, 165,   0),
    "Hard":     (220,  50,  50),
    "Insane":   (180,  40, 220),
}

# Rutas de fuentes (Poppins disponible en el sistema)
FONT_DIR   = "/usr/share/fonts/truetype/google-fonts"
FONT_BOLD  = os.path.join(FONT_DIR, "Poppins-Bold.ttf")
FONT_MED   = os.path.join(FONT_DIR, "Poppins-Medium.ttf")
FONT_REG   = os.path.join(FONT_DIR, "Poppins-Regular.ttf")
FONT_LIGHT = os.path.join(FONT_DIR, "Poppins-Light.ttf")

# Fallback a DejaVu si no están las Poppins
if not os.path.exists(FONT_BOLD):
    FONT_DIR   = "/usr/share/fonts/truetype/dejavu"
    FONT_BOLD  = os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf")
    FONT_MED   = FONT_BOLD
    FONT_REG   = os.path.join(FONT_DIR, "DejaVuSans.ttf")
    FONT_LIGHT = FONT_REG


# ─── Helpers de fuentes ───────────────────────────────────────────────────────

def font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


# ─── API de HackTheBox ────────────────────────────────────────────────────────

def get_machine_info(name_or_id: str, token: str) -> dict:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept":        "application/json",
        "User-Agent":    "HTB-Cover-Generator/1.0",
    }
    url = f"{HTB_API_BASE}/machine/profile/{name_or_id}"
    resp = requests.get(url, headers=headers, timeout=15)

    if resp.status_code == 401:
        sys.exit("❌  Token inválido o expirado. Genera uno nuevo en: "
                 "https://app.hackthebox.com/profile/settings")
    if resp.status_code == 404:
        sys.exit(f"❌  Máquina '{name_or_id}' no encontrada. "
                 "Comprueba que el nombre está bien escrito.")
    resp.raise_for_status()
    return resp.json().get("info", {})


def download_avatar(avatar_path: str, token: str) -> Image.Image | None:
    """Descarga el avatar de la máquina.

    La API devuelve avatar como '/storage/avatars/<hash>.png'.
    Las imágenes están alojadas en un bucket S3 público; construimos
    la URL a partir del nombre de fichero del hash.
    """
    if not avatar_path:
        return None

    # Extraer el nombre del fichero del path de la API
    filename = avatar_path.strip("/").split("/")[-1]

    # Candidatos de URL en orden de preferencia
    urls_to_try = [
        HTB_AVATAR_S3.format(filename=filename),          # S3 público (sin auth)
        f"{HTB_AVATAR_WWW}/storage/avatars/{filename}",   # www fallback
        f"https://labs.hackthebox.com/storage/avatars/{filename}",
    ]

    headers = {"Authorization": f"Bearer {token}", "User-Agent": "HTB-Cover-Generator/1.0"}

    for url in urls_to_try:
        try:
            resp = requests.get(url, timeout=10)   # S3 es público, no necesita auth
            if resp.status_code == 200:
                print(f"   → Avatar descargado desde: {url}")
                return Image.open(io.BytesIO(resp.content)).convert("RGBA")
        except Exception:
            continue

    # Último intento con token de auth por si alguna URL lo requiere
    try:
        resp = requests.get(urls_to_try[0], headers=headers, timeout=10)
        resp.raise_for_status()
        return Image.open(io.BytesIO(resp.content)).convert("RGBA")
    except Exception as e:
        print(f"⚠️  No se pudo descargar el avatar ({e}). Se usará placeholder.")
        return None


# ─── Utilidades de dibujo ─────────────────────────────────────────────────────

def draw_rounded_rect(draw, xy, radius, fill=None, outline=None, width=1):
    x1, y1, x2, y2 = xy
    draw.rounded_rectangle([x1, y1, x2, y2], radius=radius,
                            fill=fill, outline=outline, width=width)


def hex_to_rgb(hex_str: str):
    h = hex_str.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def make_gradient_bg(w, h, top, bot) -> Image.Image:
    """Fondo con degradado vertical."""
    img = Image.new("RGB", (w, h))
    for y in range(h):
        t = y / h
        r = int(top[0] + (bot[0] - top[0]) * t)
        g = int(top[1] + (bot[1] - top[1]) * t)
        b = int(top[2] + (bot[2] - top[2]) * t)
        for x in range(w):
            img.putpixel((x, y), (r, g, b))
    return img


def draw_grid_dots(img: Image.Image, spacing=40, alpha=18):
    """Cuadrícula de puntos sutil en el fondo."""
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for y in range(0, img.height, spacing):
        for x in range(0, img.width, spacing):
            draw.ellipse([x-1, y-1, x+1, y+1], fill=(159, 239, 0, alpha))
    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")


def draw_glowing_line(draw, y, color, width=1, alpha_frac=0.6):
    """Línea horizontal con efecto glow."""
    r, g, b = color
    draw.line([(0, y), (CANVAS_W, y)], fill=color, width=width)


def circle_avatar(avatar: Image.Image, size: int) -> Image.Image:
    """Recorta el avatar en círculo con borde verde nítido (supersampling 4x)."""
    BORDER = 5
    SCALE  = 4                          # factor de supersampling
    total  = size + BORDER * 2

    # ── Trabajar a resolución 4x ──────────────────────────────────────────────
    S = size   * SCALE
    T = total  * SCALE
    B = BORDER * SCALE

    # Círculo verde exterior a 4x
    hi = Image.new("RGBA", (T, T), (0, 0, 0, 0))
    bd = ImageDraw.Draw(hi)
    bd.ellipse([0, 0, T - 1, T - 1], fill=(*COLOR_GREEN, 255))

    # Avatar recortado en círculo a 4x
    avatar_hi = avatar.resize((S, S), Image.LANCZOS)
    mask_hi   = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask_hi).ellipse([0, 0, S - 1, S - 1], fill=255)
    result_hi = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    result_hi.paste(avatar_hi, mask=mask_hi)

    # Pegar avatar sobre el borde verde
    hi.paste(result_hi, (B, B), result_hi)

    # Anillo separador interior oscuro
    ring = ImageDraw.Draw(hi)
    sep = 2 * SCALE
    ring.ellipse([B - sep, B - sep, B + S + sep - 1, B + S + sep - 1],
                 outline=(10, 18, 30, 255), width=SCALE * 2)

    # ── Reducir a tamaño final con LANCZOS (antialiasing natural) ────────────
    return hi.resize((total, total), Image.LANCZOS)


def os_icon(os_name: str, size: int) -> Image.Image:
    """Genera un icono simple para el SO."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx, cy, r = size // 2, size // 2, size // 2 - 2

    os_lower = os_name.lower()
    if "linux" in os_lower:
        color = (255, 165, 0)   # naranja
    elif "windows" in os_lower:
        color = (0, 120, 215)   # azul Windows
    elif "freebsd" in os_lower or "openbsd" in os_lower:
        color = (220, 50, 50)
    elif "android" in os_lower:
        color = (60, 180, 75)
    else:
        color = (150, 150, 150)

    draw.ellipse([2, 2, size-2, size-2], fill=(color[0]//8, color[1]//8, color[2]//8 + 25, 255),
                 outline=(*color, 255), width=2)
    f = font(FONT_BOLD, size // 2)
    letter = os_name[0].upper() if os_name else "?"
    bbox = draw.textbbox((0, 0), letter, font=f)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((cx - tw // 2, cy - th // 2 - 2), letter, font=f, fill=(*color, 255))
    return img


def difficulty_badge(text: str, w=180, h=42) -> Image.Image:
    color = DIFFICULTY_COLORS.get(text, (150, 150, 150))
    # Fondo ligeramente más claro que el panel para que el fill sea visible
    r_bg = min(color[0] // 6, 35)
    g_bg = min(color[1] // 6, 45)
    b_bg = min(color[2] // 6 + 30, 60)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([0, 0, w-1, h-1], radius=h//2,
                            fill=(r_bg, g_bg, b_bg, 255), outline=(*color, 255), width=2)
    f = font(FONT_BOLD, 18)
    bbox = draw.textbbox((0, 0), text, font=f)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((w - tw) // 2, (h - th) // 2 - 1), text, font=f, fill=(*color, 255))
    return img


def htb_logo_text(draw, x, y):
    """Escribe el logo 'HACK THE BOX' estilizado."""
    f_htb = font(FONT_BOLD, 13)
    draw.text((x, y), "HACK THE BOX", font=f_htb, fill=(*COLOR_GREEN, 200))


# ─── Generación de portada ────────────────────────────────────────────────────

def format_date(date_str: str) -> str:
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.strftime("%d %b %Y")
    except Exception:
        return date_str[:10] if date_str else "Desconocida"


def generate_cover(info: dict, avatar_img: Image.Image | None, output_path: str):
    name        = info.get("name", "Unknown")
    os_name     = info.get("os", "Unknown")
    difficulty  = info.get("difficultyText", "Unknown")
    release_raw = info.get("release", "")
    stars       = info.get("stars", "N/A")
    points      = info.get("static_points", "?")
    release_fmt = format_date(release_raw)
    diff_color  = DIFFICULTY_COLORS.get(difficulty, (150, 150, 150))

    # ── Base ──────────────────────────────────────────────────────────────────
    canvas = make_gradient_bg(CANVAS_W, CANVAS_H, COLOR_BG_TOP, COLOR_BG_BOT)
    canvas = draw_grid_dots(canvas)
    draw   = ImageDraw.Draw(canvas)

    # ── Línea de acento superior ──────────────────────────────────────────────
    for i, alpha in enumerate([40, 80, 140, 200, 255, 200, 140, 80, 40]):
        draw.line([(0, i), (CANVAS_W, i)], fill=(*COLOR_GREEN, alpha), width=1)

    # ── Panel central ─────────────────────────────────────────────────────────
    panel_x1, panel_y1 = 60, 60
    panel_x2, panel_y2 = CANVAS_W - 60, CANVAS_H - 60
    panel_overlay = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
    panel_draw = ImageDraw.Draw(panel_overlay)
    panel_draw.rounded_rectangle(
        [panel_x1, panel_y1, panel_x2, panel_y2],
        radius=16,
        fill=(15, 25, 40, 200),
        outline=(*COLOR_BORDER, 255),
        width=1,
    )
    canvas = Image.alpha_composite(canvas.convert("RGBA"), panel_overlay).convert("RGB")
    draw   = ImageDraw.Draw(canvas)

    # ── Logo HTB (esquina superior izquierda del panel) ────────────────────────
    htb_logo_text(draw, panel_x1 + 24, panel_y1 + 18)

    # ── Línea separadora bajo el logo ─────────────────────────────────────────
    sep_y = panel_y1 + 45
    draw.line([(panel_x1 + 16, sep_y), (panel_x2 - 16, sep_y)],
              fill=(*COLOR_BORDER, 255), width=1)

    # ─────────────────────────────────────────────────────────────────────────
    # ZONA IZQUIERDA: Avatar + nombre de máquina
    # ─────────────────────────────────────────────────────────────────────────
    left_cx = panel_x1 + 220
    avatar_y = sep_y + 55
    avatar_size = 240

    BORDER = 5
    total_avatar = avatar_size + BORDER * 2
    ax = left_cx - total_avatar // 2
    ay = avatar_y

    if avatar_img:
        circ = circle_avatar(avatar_img, avatar_size)
        canvas.paste(circ, (ax, ay), circ)
    else:
        # Placeholder: dibujado directamente en el canvas con colores opacos
        # para evitar que el alpha blending lo haga invisible sobre el fondo oscuro
        placeholder = Image.new("RGBA", (total_avatar, total_avatar), (0, 0, 0, 0))
        pd = ImageDraw.Draw(placeholder)

        # Anillo verde exterior (borde sólido opaco)
        pd.ellipse([0, 0, total_avatar - 1, total_avatar - 1],
                   fill=(*COLOR_GREEN, 255))
        # Separador interior oscuro
        pd.ellipse([BORDER - 2, BORDER - 2, BORDER + avatar_size + 1, BORDER + avatar_size + 1],
                   fill=(10, 18, 30, 255))
        # Relleno interior con color visible (más claro que el fondo del panel)
        pd.ellipse([BORDER, BORDER, BORDER + avatar_size - 1, BORDER + avatar_size - 1],
                   fill=(22, 42, 68, 255))

        # Letra inicial de la máquina
        pf = font(FONT_BOLD, 90)
        letter = name[0].upper()
        bbox = pd.textbbox((0, 0), letter, font=pf)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        tx = (total_avatar - tw) // 2 - bbox[0]
        ty = (total_avatar - th) // 2 - bbox[1] - 4
        pd.text((tx, ty), letter, font=pf, fill=(*COLOR_GREEN, 255))

        canvas.paste(placeholder, (ax, ay), placeholder)

    # Badge de dificultad bajo el avatar
    badge = difficulty_badge(difficulty, 170, 38)
    bx = left_cx - badge.width // 2
    by = ay + total_avatar + 14
    canvas.paste(badge, (bx, by), badge)

    # ─────────────────────────────────────────────────────────────────────────
    # ZONA DERECHA: Información de la máquina
    # ─────────────────────────────────────────────────────────────────────────
    info_x = panel_x1 + 470
    info_y = sep_y + 60

    # Nombre de la máquina
    f_name_big = font(FONT_BOLD, 72)
    # Ajustar tamaño si el nombre es largo
    max_name_w = panel_x2 - info_x - 30
    test_bbox = draw.textbbox((0, 0), name, font=f_name_big)
    name_w = test_bbox[2] - test_bbox[0]
    if name_w > max_name_w:
        scale = max_name_w / name_w
        new_size = max(30, int(72 * scale))
        f_name_big = font(FONT_BOLD, new_size)

    draw.text((info_x, info_y), name, font=f_name_big, fill=COLOR_WHITE)

    # Subrayado verde bajo el nombre
    name_bbox = draw.textbbox((info_x, info_y), name, font=f_name_big)
    line_y = name_bbox[3] + 8
    draw.line([(info_x, line_y), (info_x + 120, line_y)],
              fill=COLOR_GREEN, width=3)

    # ── Datos de la máquina ───────────────────────────────────────────────────
    row_y = line_y + 40
    row_gap = 68

    def data_row(label, value, y, icon_img=None, val_color=COLOR_WHITE):
        f_label = font(FONT_REG, 15)
        f_value = font(FONT_BOLD, 26)

        draw.text((info_x, y), label.upper(), font=f_label, fill=COLOR_GREY)
        val_y = y + 22

        if icon_img:
            icon_resized = icon_img.resize((28, 28), Image.LANCZOS)
            canvas.paste(icon_resized, (info_x, val_y - 2), icon_resized)
            draw.text((info_x + 36, val_y), value, font=f_value, fill=val_color)
        else:
            draw.text((info_x, val_y), value, font=f_value, fill=val_color)

    # Sistema operativo
    os_img = os_icon(os_name, 32)
    data_row("Sistema operativo", os_name, row_y, icon_img=os_img)

    # Fecha de lanzamiento
    data_row("Fecha de lanzamiento", release_fmt, row_y + row_gap)

    # Puntos
    data_row("Puntos", f"{points} pts", row_y + row_gap * 2,
             val_color=(*COLOR_GREEN,))

    # Valoración con estrellas
    star_label_y = row_y + row_gap * 3
    f_label_sm = font(FONT_REG, 15)
    draw.text((info_x, star_label_y), "VALORACIÓN", font=f_label_sm, fill=COLOR_GREY)

    try:
        stars_float = float(stars)
    except (ValueError, TypeError):
        stars_float = 0.0

    star_y = star_label_y + 24
    star_size = 22
    star_gap  = 28
    for i in range(5):
        threshold = stars_float - i
        sx = info_x + i * star_gap
        if threshold >= 1.0:
            star_col = (255, 200, 0)     # llena
        elif threshold > 0:
            star_col = (200, 150, 30)    # media
        else:
            star_col = (50, 60, 75)      # vacía
        # Dibuja estrella como polígono
        cx2 = sx + star_size // 2
        cy2 = star_y + star_size // 2
        r_out = star_size // 2
        r_in  = r_out // 2
        pts = []
        for j in range(10):
            angle = math.pi / 5 * j - math.pi / 2
            r = r_out if j % 2 == 0 else r_in
            pts.append((cx2 + r * math.cos(angle), cy2 + r * math.sin(angle)))
        draw.polygon(pts, fill=star_col)

    f_stars_val = font(FONT_BOLD, 20)
    draw.text((info_x + 5 * star_gap + 8, star_y + 2),
              f"{stars_float:.1f}",
              font=f_stars_val, fill=(255, 200, 0))

    # ── Línea de acento inferior ──────────────────────────────────────────────
    bot_y = panel_y2 - 1
    for i, alpha in enumerate([40, 80, 140, 200, 255, 200, 140, 80, 40]):
        draw.line([(0, CANVAS_H - i - 1), (CANVAS_W, CANVAS_H - i - 1)],
                  fill=(*COLOR_GREEN, alpha), width=1)

    # ── Marca de agua / footer ────────────────────────────────────────────────
    f_foot = font(FONT_LIGHT, 13)
    draw.text((panel_x2 - 220, panel_y2 - 28),
              "app.hackthebox.com",
              font=f_foot, fill=(*COLOR_GREY, 150))

    # ── Guardar ───────────────────────────────────────────────────────────────
    canvas.save(output_path, "PNG", optimize=True)
    print(f"✅  Portada guardada en: {output_path}")


# ─── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Genera una portada visual con los datos de una máquina HackTheBox.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python3 htb_cover.py Principal   --token eyJ...
  python3 htb_cover.py RouterSpace --token eyJ... --output ~/Desktop/portada.png

Obtén tu API token en:
  https://app.hackthebox.com/profile/settings  (sección "App Tokens")
        """,
    )
    parser.add_argument("machine",
                        help="Nombre o ID numérico de la máquina (p. ej. 'Principal', '622')")
    parser.add_argument("--token", "-t", required=True,
                        help="API Token de HackTheBox (Bearer token)")
    parser.add_argument("--output", "-o", default=None,
                        help="Ruta de salida para la imagen PNG. "
                             "Por defecto: <nombre_maquina>_cover.png")
    args = parser.parse_args()

    machine_slug = args.machine.strip()
    output_path  = args.output or f"{machine_slug.lower().replace(' ', '_')}_cover.png"

    print(f"🔍  Obteniendo información de la máquina: {machine_slug}")
    info = get_machine_info(machine_slug, args.token)

    name   = info.get("name", machine_slug)
    avatar = info.get("avatar", "")
    print(f"   → Máquina encontrada: {name} "
          f"[{info.get('os', '?')} | {info.get('difficultyText', '?')}]")

    avatar_img = None
    if avatar:
        print(f"🖼️   Descargando avatar...")
        avatar_img = download_avatar(avatar, args.token)

    print(f"🎨  Generando portada...")
    generate_cover(info, avatar_img, output_path)


if __name__ == "__main__":
    main()
