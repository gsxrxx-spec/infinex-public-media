# INFINEX — Publicador Instagram diario

Software de publicaciones orgánicas de @infinex_2025, sin relación con AUTOIMPORT.
- Horario de GitHub Actions: **09:30 Europe/Madrid** (horario peninsular con cambio de hora).
- Verificación adicional: **09:45 Europe/Madrid**.
- Requiere GitHub Actions habilitado y secreto `INFINEX_IG_TOKEN` configurado en Settings > Secrets and variables > Actions.
- Publicador no necesita el PC encendido ni Desktop Commander conectado.
- El horario en GitHub Actions es **planificado, no garantizado al minuto**: sus ejecuciones pueden retrasarse o perderse por carga del proveedor.
- Incluye 3 fotografías reales de Pexels por carrusel y logo de INFINEX original en esquina superior izquierda.
- Copyright: `assets/photo_library.json` registra URLs de foto y licencia oficial Pexels.
- Nunca se representa una foto de archivo como trabajo ejecutado por INFINEX.
- No se publican nombres de clientes, garantías, homologaciones ni precios.
- Contiene ledger por día `records/YYYY-MM-DD.json` para evitar POST duplicados. Si el resultado es incierto, no reintenta.
- Revisa estado en Actions; cada post VERIFICADO registra el permalink público en su ledger.
- Ejecución manual segura: `workflow_dispatch` modo `dry_run` (por defecto) nunca publica.
- Configuración exclusiva de INFINEX. Ningún token de AutoImport se utiliza ni se almacena.
- Los cambios en el horario o el flujo deben probarse antes de declararse listos.
