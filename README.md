# HTB Cover Generator

Genera una portada visual en formato PNG con la información básica de cualquier máquina de [HackTheBox](https://www.hackthebox.com), lista para usar en writeups, presentaciones o repositorios.

![Demo 1](portada.png)

---

## Características

- Consulta automática a la API oficial de HackTheBox
- Descarga el avatar real de la máquina
- Muestra nombre, sistema operativo, dificultad, fecha de lanzamiento, puntos y valoración
- Badge de dificultad con color dinámico (Easy / Medium / Hard / Insane)
- Borde del avatar con antialiasing mediante supersampling 4x
- Paleta de colores oficial de HTB (`#9FEF00`)
- Imagen de salida en PNG a resolución 1200×675 (16:9)
- Fuente Poppins con fallback automático a DejaVu Sans

---

## Requisitos

- Python 3.10 o superior
- Las siguientes librerías:

```bash
pip install requests Pillow
```

> La fuente **Poppins** debe estar instalada en el sistema. En Debian/Ubuntu:
> ```bash
> sudo apt install fonts-google-poppins
> ```
> Si no está disponible, el script usa DejaVu Sans automáticamente.

---

## Uso

```bash
python3 cover_generator.py <nombre_maquina> --token <tu_api_token>
```

### Argumentos

| Argumento | Alias | Descripción |
|-----------|-------|-------------|
| `machine` | | Nombre o ID numérico de la máquina (ej: `Principal`, `622`) |
| `--token` | `-t` | API token de HackTheBox (**obligatorio**) |
| `--output` | `-o` | Ruta de salida del PNG. Por defecto: `<nombre>_cover.png` |

### Ejemplos

```bash
# Uso básico (guarda en principal_cover.png)
python3 cover_generator.py Principal --token eyJhbGci...

# Especificar ruta de salida
python3 cover_generator.py RouterSpace --token eyJhbGci... --output ~/Desktop/portada.png

# Usando el ID numérico de la máquina
python3 cover_generator.py 622 --token eyJhbGci...
```

---

## Obtener el API Token

1. Inicia sesión en [app.hackthebox.com](https://app.hackthebox.com)
2. Ve a **Profile → Settings**
3. En la sección **App Tokens**, crea un nuevo token
4. Copia el token generado y úsalo con el argumento `--token`

---

## Información mostrada en la portada

| Campo | Fuente |
|-------|--------|
| Nombre de la máquina | API HTB |
| Avatar / icono | Bucket S3 público de HTB |
| Sistema operativo | API HTB |
| Dificultad | API HTB |
| Fecha de lanzamiento | API HTB |
| Puntos | API HTB |
| Valoración (estrellas) | API HTB |

---

## Estructura del proyecto

```
htb-cover-generator/
├── cover_generator.py       # Script principal
├── README.md          # Este fichero
└── portada.png        # Imagen de ejemplo
```

---

## Notas

- El script no requiere que la máquina esté activa o retirada; funciona con cualquier máquina a la que tengas acceso con tu cuenta.
- Si el avatar no puede descargarse (por cambios en la infraestructura de HTB), se genera un placeholder con la inicial del nombre de la máquina.
- Los mensajes de consola del script están en español.
