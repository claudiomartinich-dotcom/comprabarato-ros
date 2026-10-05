"""
Baja productos y precios de Coto Digital y los guarda en data/coto.csv

Usa el mismo buscador que usa la página de Coto (el pedido que se ve en DevTools).
Uso:
    python scraper/coto_scraper.py                 -> usa scraper/terminos.txt
    python scraper/coto_scraper.py aceite arroz    -> solo esas búsquedas
"""
import csv
import sys
import time
import uuid
from datetime import date
from pathlib import Path
from urllib.parse import quote

import requests

API = "https://api.coto.com.ar/api/v1/ms-digital-sitio-bff-web/api/v1/products/search/"
CLAVE = "key_r6xzz4IAoTWcipni"   # clave pública que usa la propia página de Coto
SUCURSAL = "200"                  # sucursal de la que se toman los precios
POR_PAGINA = 100                  # si Coto no lo acepta, el script baja solo a 24
PAUSA = 1.0
MAX_PAGINAS = 40

HEADERS = {
    "Accept": "application/json",
    "Origin": "https://www.coto.com.ar",
    "Referer": "https://www.coto.com.ar/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36",
}
CLIENTE = str(uuid.uuid4())


def a_numero(v):
    """'$5970.45' -> 5970.45 ; 7464 -> 7464.0 ; None -> None"""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).replace("$", "").replace(" ", "")
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def parsear(resultado, sucursal=SUCURSAL):
    """Convierte un resultado de la API en una fila, o None si no sirve."""
    d = resultado.get("data", {})
    nombre = (d.get("sku_display_name") or d.get("sku_description") or "").strip()
    lista = next((p for p in d.get("price", []) if str(p.get("store")) == sucursal), None)
    if not nombre or not lista:
        return None
    regular = a_numero(lista.get("listPrice"))
    if not regular:
        return None
    precio, oferta = regular, ""
    desc = (d.get("discounts") or [None])[0]
    if desc:
        con_desc = a_numero(desc.get("discountPrice"))
        if con_desc and 0 < con_desc < regular:
            precio = con_desc
            oferta = (desc.get("discountText") or "si").strip()
    return {
        "codigo": str(d.get("sku_plu") or d.get("id") or ""),
        "producto": " ".join(nombre.split()),
        "precio": f"{precio:.2f}",
        "oferta": oferta,
        "precio_regular": f"{regular:.2f}",
        "ean": str(d.get("product_main_ean") or ""),
    }


def pedir(sesion, termino, pagina, por_pagina):
    params = {
        "key": CLAVE,
        "num_results_per_page": por_pagina,
        "page": pagina,
        "pre_filter_expression": '{"name":"store_availability","value":"%s"}' % SUCURSAL,
        "c": "cio-fe-web-coto-4.4.0",
        "i": CLIENTE,
        "s": 1,
        "origin_referrer": "/productos/" + termino,
        "us": SUCURSAL,
    }
    r = sesion.get(API + quote(termino), params=params, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json().get("response", {})


def buscar(sesion, termino, por_pagina):
    filas = []
    for pagina in range(1, MAX_PAGINAS + 1):
        resp = pedir(sesion, termino, pagina, por_pagina)
        resultados = resp.get("results", [])
        for r in resultados:
            fila = parsear(r)
            if fila:
                filas.append(fila)
        if len(resultados) < por_pagina:
            break
        time.sleep(PAUSA)
    return filas


def main():
    global POR_PAGINA
    if len(sys.argv) > 1:
        terminos = sys.argv[1:]
    else:
        archivo = Path(__file__).parent / "terminos.txt"
        if not archivo.exists():
            sys.exit("Falta scraper/terminos.txt o pasá palabras: python coto_scraper.py aceite")
        terminos = [t.strip() for t in archivo.read_text(encoding="utf-8").splitlines() if t.strip()]

    sesion = requests.Session()
    todos = {}
    for i, t in enumerate(terminos, 1):
        try:
            try:
                res = buscar(sesion, t, POR_PAGINA)
            except requests.HTTPError as e:
                if POR_PAGINA != 24 and e.response is not None and e.response.status_code == 400:
                    POR_PAGINA = 24
                    res = buscar(sesion, t, POR_PAGINA)
                else:
                    raise
        except Exception as e:
            print(f"[{i}/{len(terminos)}] {t}: error ({e})")
            continue
        nuevos = 0
        for p in res:
            clave = p["codigo"] or p["producto"]
            if clave not in todos:
                todos[clave] = p
                nuevos += 1
        print(f"[{i}/{len(terminos)}] {t}: {len(res)} resultados, {nuevos} nuevos")
        time.sleep(PAUSA)

    if not todos:
        sys.exit("No se obtuvo ningún producto: no se actualiza coto.csv")
    hoy = date.today().isoformat()
    Path("data").mkdir(exist_ok=True)
    with open("data/coto.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["super", "codigo", "producto", "precio", "oferta", "fecha", "precio_regular", "ean"])
        for p in todos.values():
            w.writerow(["COTO", p["codigo"], p["producto"], p["precio"], p["oferta"], hoy, p["precio_regular"], p["ean"]])
    print(f"Listo: {len(todos)} productos guardados en data/coto.csv")


if __name__ == "__main__":
    main()
