# INFINEX — Dos carruseles diarios en Instagram

Software de publicaciones orgánicas de @infinex_2025, sin relación con AUTOIMPORT.

- **09:00 y 17:00 Europe/Madrid:** un carrusel diferente por franja, con tres fotografías con licencia comercial.
- **09:15 y 17:15 Europe/Madrid:** consulta independiente para confirmar el resultado.
- GitHub Actions realiza el trabajo sin necesidad de encender el PC o tener abierto ChatGPT.
- Horarios planificados, no garantizados al minuto: GitHub puede retrasar u omitir alguna ejecución.
- Secreto GitHub Actions `INFINEX_IG_TOKEN` protegido; no escribir credenciales en archivos, historial o logs.
- Logo INFINEX original completo en esquina; colores negro, blanco y naranja.
- Fotos de Pexels con origen/licencia documentados; jamás presentarlas como obras reales de INFINEX.
- Registros independientes `records/YYYY-MM-DD_09.json` y `records/YYYY-MM-DD_17.json`.
- Archivos de imagen independientes `assets/daily/YYYY-MM-DD/09/` y `/17/`.
- Si Meta genera resultado incierto, no repetir el POST automáticamente. No mezclar cuentas ni tokens de AutoImport.
- `workflow_dispatch` permite `dry_run` (por defecto), `publish` y `verify`, seleccionando franja 09 o 17.
- La primera ejecución automática real en cada franja y su comprobación posterior siguen pendientes de prueba.
