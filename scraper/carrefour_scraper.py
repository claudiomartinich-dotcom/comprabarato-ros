"""
Baja productos y precios de Carrefour Argentina y los guarda en data/carrefour.csv

Usa el buscador abierto de la tienda (VTEX), el mismo que usa la página.
Uso:
    python scraper/carrefour_scraper.py                 -> usa scraper/terminos.txt
    python scraper/carrefour_scraper.py aceite arroz    -> solo esas búsquedas
"""
import csv
import sys
import time
from datetime import date
from pathlib import Path

import requests

API = "https://www.carrefour.com.ar/api/io/_v/api/intelligent-search/product_search/"
POR_PAGINA = 50
PAUSA = 1.0
MAX_PAGINAS = 30

HEADERS = {
    "Accept": "application/json",
    "Accept-Language": "es-AR,es;q=0.9",
    "Referer": "https://www.carrefour.com.ar/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36",
}


def ean_de(p):
    """Busca el código de barras en los items del producto o en sus especificaciones."""
    for it in p.get("items") or []:
        e = str(it.get("ean") or "").strip()
        if e:
            return e
    for g in p.get("specificationGroups") or []:
        for sp in g.get("specifications") or []:
            if str(sp.get("name", "")).strip().upper() == "EAN" and sp.get("values"):
                return str(sp["values"][0]).strip()
    return ""


def parsear(p):
    """Convierte un producto de la API en una fila, o None si no sirve."""
    nombre = " ".join(str(p.get("productName") or "").split())
    rango = p.get("priceRange") or {}
    venta = (rango.get("sellingPrice") or {}).get("lowPrice")
    lista = (rango.get("listPrice") or {}).get("lowPrice")
    if not nombre or not venta or venta <= 0:
        return None
    oferta = "si" if lista and venta < lista else ""
    return {
        "codigo": str(p.get("productId") or ""),
        "producto": nombre,
        "precio": f"{float(venta):.2f}",
        "oferta": oferta,
        "precio_regular": f"{float(lista or venta):.2f}",
        "ean": ean_de(p),
    }


def pedir(sesion, termino, pagina):
    params = {"query": termino, "page": pagina, "count": POR_PAGINA,
              "locale": "es-AR", "hideUnavailableItems": "true"}
    for intento in range(3):
        r = sesion.get(API, params=params, headers=HEADERS, timeout=30)
        if r.status_code == 429:
            time.sleep(5 * (intento + 1))
            continue
        r.raise_for_status()
        return r.json()
    r.raise_for_status()


def buscar(sesion, termino):
    filas = []
    for pagina in range(1, MAX_PAGINAS + 1):
        data = pedir(sesion, termino, pagina)
        productos = data.get("products") or []
        for p in productos:
            fila = parsear(p)
            if fila:
                filas.append(fila)
        total = data.get("recordsFiltered")
        if len(productos) < POR_PAGINA or (total is not None and pagina * POR_PAGINA >= total):
            break
        time.sleep(PAUSA)
    return filas


def main():
    if len(sys.argv) > 1:
        terminos = sys.argv[1:]
    else:
        archivo = Path(__file__).parent / "terminos.txt"
        if not archivo.exists():
            sys.exit("Falta scraper/terminos.txt o pasá palabras: python carrefour_scraper.py aceite")
        terminos = [t.strip() for t in archivo.read_text(encoding="utf-8").splitlines() if t.strip()]

    sesion = requests.Session()
    todos = {}
    for i, t in enumerate(terminos, 1):
        try:
            res = buscar(sesion, t)
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
        sys.exit("No se obtuvo ningún producto: no se actualiza carrefour.csv")
    hoy = date.today().isoformat()
    Path("data").mkdir(exist_ok=True)
    with open("data/carrefour.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["super", "codigo", "producto", "precio", "oferta", "fecha", "precio_regular", "ean"])
        for p in todos.values():
            w.writerow(["Carrefour", p["codigo"], p["producto"], p["precio"], p["oferta"], hoy, p["precio_regular"], p["ean"]])
    print(f"Listo: {len(todos)} productos guardados en data/carrefour.csv")


if __name__ == "__main__":
    main()
