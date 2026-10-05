// Listas de precios que lee la app. Una línea por supermercado.
// "url" puede ser un archivo de esta carpeta (data/dar.csv) o el link CSV de una planilla de Google Sheets.
const FUENTES = [
  { nombre: "DAR", url: "data/dar.csv" },
  { nombre: "COTO", url: "data/coto.csv" },
  { nombre: "Carrefour", url: "data/carrefour.csv" },
  { nombre: "Super Empleados", url: "https://docs.google.com/spreadsheets/d/e/2PACX-1vR3pfVG-p5ypuhA0tShrm43pXlRuLtvah7eJRwCXYmzTElG42YkVrO0QHRYIqQItI4VtlU9rjI5ynUC/pub?gid=0&single=true&output=csv" },
];
