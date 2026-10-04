// Listas de precios que lee la app. Una línea por supermercado.
// "url" puede ser un archivo de esta carpeta (data/dar.csv) o el link CSV de una planilla de Google Sheets.
const FUENTES = [
  { nombre: "DAR", url: "data/dar.csv" },
  // { nombre: "COTO", url: "data/coto.csv" },   // se activa cuando sumemos COTO
  { nombre: "Super Empleados", url: "PEGAR_ACA_EL_LINK_CSV_DE_GOOGLE_SHEETS" },
];
