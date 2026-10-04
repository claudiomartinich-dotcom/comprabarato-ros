"""
Baja productos y precios de darentucasa.com.ar y los guarda en data/dar.csv

Uso (en tu PC, con Python 3 instalado):
    pip install requests
    python dar_scraper.py                 -> usa las búsquedas de terminos.txt (una por línea)
    python dar_scraper.py aceite arroz    -> busca solo esas palabras

Cada corrida actualiza dar.csv. Después lo cargás en la app como "DAR".
"""
import csv
import html
import re
import sys
import time
from datetime import date
from pathlib import Path

import requests

BASE = "https://darentucasa.com.ar"
PAUSA = 1.0          # segundos entre pedidos, para no cargar el sitio
MAX_PAGINAS = 60     # tope de seguridad por búsqueda

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": BASE + "/carrito.asp",
    "Accept": "text/html, */*; q=0.01",
}

RE_ITEM = re.compile(r'<li class="cuadProd">(.*?)</li>', re.S)
RE_COD = re.compile(r"Detalle\.asp\?Pr=(\d+)")
RE_DESC = re.compile(r'class="desc[^"]*">(.*?)</div>', re.S)
RE_PRECIO = re.compile(r"class='izq'>\$([\d.]+),<b>(\d+)</b>")
RE_PAG = re.compile(r"(\d+)\s+de\s+(\d+)")


def bajar(sesion, url):
    r = sesion.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    try:
        return r.content.decode("utf-8")
    except UnicodeDecodeError:
        return r.content.decode("cp1252", errors="replace")


def parsear(texto):
    productos = []
    for bloque in RE_ITEM.findall(texto):
        cod = RE_COD.search(bloque)
        desc = RE_DESC.search(bloque)
        precio = RE_PRECIO.search(bloque)
        if not (cod and desc and precio):
            continue
        entero = precio.group(1).replace(".", "")
        productos.append({
            "codigo": cod.group(1),
            "producto": html.unescape(re.sub(r"\s+", " ", desc.group(1))).strip(),
            "precio": f"{entero}.{precio.group(2)}",
            "oferta": "si" if "OferProd" in bloque else "",
        })
    return productos


def buscar(sesion, termino):
    """Devuelve todos los productos de una búsqueda, recorriendo las páginas."""
    encontrados = []
    texto = bajar(sesion, f"{BASE}/Productos.asp?cpoBuscar={requests.utils.quote(termino)}")
    total = 1
    pag = 1
    while True:
        encontrados += parsear(texto)
        m = RE_PAG.search(re.sub(r"<[^>]+>|&nbsp;", " ", texto.split("</ul>")[-1]))
        if m:
            total = int(m.group(2))
        if pag >= total or pag >= MAX_PAGINAS:
            break
        pag += 1
        time.sleep(PAUSA)
        texto = bajar(sesion, f"{BASE}/productos.asp?page={pag}&N1=&N2=&N3=&N4=")
    return encontrados


def main():
    if len(sys.argv) > 1:
        terminos = sys.argv[1:]
    else:
        archivo = Path(__file__).parent / "terminos.txt"
        if not archivo.exists():
            sys.exit("Creá terminos.txt (una búsqueda por línea) o pasá palabras: python dar_scraper.py aceite")
        terminos = [t.strip() for t in archivo.read_text(encoding="utf-8").splitlines() if t.strip()]

    sesion = requests.Session()
    sesion.get(BASE + "/", headers=HEADERS, timeout=30)      # toma su propia cookie de sesión
    sesion.cookies.set("cantP", "50", domain="darentucasa.com.ar")  # 50 productos por página

    todos = {}
    for i, t in enumerate(terminos, 1):
        try:
            res = buscar(sesion, t)
        except Exception as e:
            print(f"[{i}/{len(terminos)}] {t}: error ({e})")
            continue
        nuevos = 0
        for p in res:
            if p["codigo"] not in todos:
                todos[p["codigo"]] = p
                nuevos += 1
        print(f"[{i}/{len(terminos)}] {t}: {len(res)} resultados, {nuevos} nuevos")
        time.sleep(PAUSA)

    if not todos:
        sys.exit("No se obtuvo ningún producto: no se actualiza dar.csv")
    hoy = date.today().isoformat()
    Path("data").mkdir(exist_ok=True)
    with open("data/dar.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["super", "codigo", "producto", "precio", "oferta", "fecha"])
        for p in todos.values():
            w.writerow(["DAR", p["codigo"], p["producto"], p["precio"], p["oferta"], hoy])
    print(f"Listo: {len(todos)} productos guardados en data/dar.csv")


if __name__ == "__main__":
    main()
