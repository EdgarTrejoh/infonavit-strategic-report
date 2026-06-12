# Cloud Run Deployment Checklist - API INFONAVIT

Este documento prepara el despliegue futuro de la API FastAPI en Google Cloud Run. No ejecutar despliegues hasta cerrar seguridad, costos y secretos.

## 1. Pre-requisitos

- [ ] Proyecto GCP definido.
- [ ] Billing activo.
- [ ] Presupuesto configurado antes del despliegue.
- [ ] Alertas de gasto configuradas.
- [ ] `gcloud` CLI instalado y autenticado.
- [ ] Docker funcionando localmente.
- [ ] Artifact Registry o Cloud Build definido.
- [ ] Repo limpio.
- [ ] `python -m pytest -q` pasando.
- [ ] Imagen Docker validada localmente.

## 2. Configuracion recomendada de Cloud Run

- `min instances = 0`.
- `max instances = 1` o `2` para controlar gasto inicial.
- Memoria inicial: `512Mi` o `1Gi`.
- CPU bajo demanda.
- Timeout moderado.
- Concurrencia controlada.
- Region definida antes de publicar.
- Logs sin credenciales ni connection strings.
- Revision de costo antes de exponer endpoints.

## 3. Variables y secretos

- `DATABASE_URL` no debe ir en Git.
- `INFONAVIT_API_KEY` no debe ir en Git.
- No usar `.env` en produccion.
- Usar Secret Manager o variables seguras de Cloud Run.
- `DATABASE_URL` de Cloud Run debe apuntar a un usuario PostgreSQL/Supabase read-only.
- La credencial admin/migration no debe configurarse en Cloud Run.
- No imprimir `DATABASE_URL`.
- No imprimir `DB_PASSWORD`.
- No imprimir `INFONAVIT_API_KEY`.
- No imprimir connection strings.
- No pegar credenciales en README, Notion, issues, tickets ni logs.

## 4. Endpoints a validar en Cloud Run

- `GET /health`
- `GET /db/health` con header `X-API-Key`
- `GET /mini-report/json` con header `X-API-Key`
- `GET /mini-report/markdown` con header `X-API-Key`

## 5. Seguridad minima antes de exponer publicamente

- No exponer publicamente sin control.
- Usar API key por header `X-API-Key` para endpoints operativos.
- Documentar que la API es solo lectura.
- No habilitar endpoints de escritura.
- No habilitar migraciones desde API.
- No habilitar carga de archivos desde API.
- No integrar IA antes de cerrar control de acceso.

## 6. Seguridad SQL/API

- No construir SQL con f-strings usando parametros del usuario.
- No concatenar strings SQL con query params.
- Usar SQLAlchemy `text()` con bind parameters.
- Validar tipos y rangos de parametros HTTP.
- Limitar parametros a `int` donde aplique.
- Validar rangos razonables para anios y `month_limit`.
- No exponer errores crudos de SQLAlchemy/psycopg2.
- Usar usuario de base con permisos minimos en produccion.
- La API debe usar un usuario con permisos `SELECT`.
- El migrador debe usar una credencial admin/migration separada para cargas y upsert.
- No crear tabla `app_users` todavia; queda para una fase posterior con login, clientes, permisos por usuario o auditoria funcional.
- Mantener endpoints de solo lectura.
- No permitir que la IA ejecute SQL.

## 7. Comandos futuros sugeridos - NO EJECUTAR TODAVIA

Estos comandos son ejemplos para una fase posterior.

```powershell
docker build -t infonavit-strategic-report-api .
```

```powershell
docker tag infonavit-strategic-report-api REGION-docker.pkg.dev/PROJECT_ID/REPOSITORY/infonavit-strategic-report-api:latest
```

```powershell
docker push REGION-docker.pkg.dev/PROJECT_ID/REPOSITORY/infonavit-strategic-report-api:latest
```

```powershell
gcloud run deploy infonavit-strategic-report-api `
  --image REGION-docker.pkg.dev/PROJECT_ID/REPOSITORY/infonavit-strategic-report-api:latest `
  --region REGION `
  --platform managed `
  --min-instances 0 `
  --max-instances 1 `
  --memory 512Mi
```

## 8. Checklist final antes de deploy

- [ ] `pytest` pasa.
- [ ] Docker local pasa.
- [ ] `/health` local pasa.
- [ ] `/db/health` local pasa con `X-API-Key`.
- [ ] `/mini-report/json` local pasa con `X-API-Key`.
- [ ] `/mini-report/markdown` local pasa con `X-API-Key`.
- [ ] `.env` no versionado.
- [ ] `DATABASE_URL` configurado como secreto.
- [ ] `DATABASE_URL` usa usuario read-only para API.
- [ ] Credencial admin/migration fuera de Cloud Run.
- [ ] `INFONAVIT_API_KEY` configurado como secreto.
- [ ] Presupuesto GCP configurado.
- [ ] Alertas GCP configuradas.
- [ ] Limite de instancias definido.
- [ ] Seguridad minima por `X-API-Key` validada.
- [ ] Revision de parametros API completada.
- [ ] Revision de SQL injection completada.
- [ ] Usuario de base con permisos minimos definido.
- [ ] `SELECT COUNT(*)` funciona con usuario read-only.
- [ ] `INSERT`, `UPDATE` y `DELETE` fallan con usuario read-only.
