# Frontend Strategy - INFONAVIT Strategic Report

## 1. Objetivo

Definir la estrategia inicial para construir un frontend que consuma la API `infonavit-strategic-report-api` sin afectar la estabilidad del backend actual validado en Cloud Run.

El frontend debe facilitar el consumo del reporte extendido y del analisis asistido por IA para usuarios no tecnicos, manteniendo el backend como fuente de verdad.

Adicionalmente, debe sentar las bases para:

- generar graficas visuales con base en el periodo seleccionado;
- generar un mini reporte PDF con graficas y salidas de IA;
- permitir que solo usuarios registrados descarguen reportes o accedan a funcionalidades de IA.

## 2. Estado base

Backend actual:

- Repositorio: `infonavit-strategic-report`.
- API FastAPI publicada en Cloud Run.
- Fuente de datos: Supabase PostgreSQL read-only.
- Seguridad minima: `X-API-Key`.
- Documentacion FastAPI desactivada en produccion con `ENVIRONMENT=production`.
- Release validada: `v0.10.0-ai-executive-engine`.
- Validacion productiva end-to-end completada el 2026-06-17.
- Pruebas vigentes: `144 passed`.

Endpoints relevantes:

- `GET /health`
- `GET /db/health`
- `GET /mini-report/extended/json`
- `GET /mini-report/extended/markdown`
- `GET /mini-report/ai/json`
- `GET /mini-report/ai/markdown`

## 3. Decision recomendada

Crear un proyecto frontend separado:

```text
infonavit-strategic-report-ui
```

Mantener el backend en:

```text
infonavit-strategic-report
```

Motivos:

- Evita mezclar dependencias Python/backend con tooling frontend.
- Permite versionar y desplegar frontend y API de forma independiente.
- Reduce riesgo sobre el backend productivo ya estable.
- Facilita adoptar un patron server-side para no exponer `X-API-Key` en navegador.
- Facilita controlar acceso por usuario antes de permitir descargas o uso de IA.
- Facilita generar PDF en servidor sin exponer secretos ni cargar logica pesada en el navegador.
- Permite evolucionar UI sin tocar ETL, migraciones ni visualizaciones actuales del backend.

## 4. Alternativas consideradas

### Opcion A - Nuevo repositorio frontend

Recomendada.

Ventajas:

- Separacion clara de responsabilidades.
- CI independiente.
- Deploy independiente.
- Menor riesgo sobre backend.
- Mejor preparacion para autenticacion y proxy server-side.

Riesgos:

- Requiere coordinar dos repositorios.
- Requiere documentar contrato API y variables de entorno.

### Opcion B - Monorepo dentro del backend

No recomendada para la primera version.

Ventajas:

- Un solo repositorio.
- Mas facil de descubrir localmente.

Riesgos:

- Mezcla dependencias y pipelines.
- Puede complicar CI.
- Aumenta el ruido en el repo backend.
- Puede inducir cambios accidentales en API estable.

### Opcion C - Front minimo estatico

Viable solo para prototipo interno.

Ventajas:

- Rapido.
- Poco tooling.

Riesgos:

- Si llama directo a Cloud Run, puede exponer `X-API-Key`.
- Limitado para evolucionar autenticacion, sesiones, permisos, PDF server-side o proxy seguro.

## 5. Stack recomendado

Recomendacion principal:

```text
Next.js + TypeScript + Tailwind CSS
```

Motivos:

- Permite llamadas server-side a la API sin exponer `X-API-Key` al navegador.
- Facilita crear API routes/proxy si se requiere.
- Buen soporte para formularios, estados de carga, render de Markdown y rutas protegidas.
- Permite generar PDF server-side o delegarlo a una ruta segura.
- Facil despliegue en Vercel, Cloud Run o infraestructura equivalente.

Alternativa simple:

```text
Vite + React + TypeScript
```

Usarla solo si el frontend sera estrictamente local/interno y se acepta manejar seguridad de forma limitada.

## 6. Principio de seguridad

El frontend no debe exponer secretos.

No debe exponerse en el navegador:

- `X-API-Key`.
- `INFONAVIT_API_KEY`.
- `OPENAI_API_KEY`.
- `DATABASE_URL`.
- Credenciales Supabase.
- Secretos de autenticacion.

Patron recomendado para produccion:

```text
Browser
-> Frontend server-side / API route
-> Cloud Run API con X-API-Key
-> Supabase / OpenAI / inflacion-copilot-api
```

En este patron:

- El usuario interactua con el frontend.
- El frontend server-side llama a la API backend.
- `X-API-Key` vive en el entorno seguro del frontend, no en el browser.
- La API backend sigue siendo read-only.
- Las descargas y uso de IA pueden validarse contra permisos de usuario antes de llamar al backend.

Para prototipo local privado puede usarse una key local, pero no debe publicarse asi.

## 7. Alcance MVP

El MVP debe enfocarse en consumo, visualizacion, exportacion y control de acceso minimo.

Incluye:

- Seleccionar:
  - anio actual;
  - anio previo;
  - mes de corte.
- Consultar reporte extendido JSON.
- Consultar reporte extendido Markdown.
- Consultar analisis asistido por IA JSON.
- Consultar analisis asistido por IA Markdown.
- Generar graficas visuales basadas en el periodo seleccionado.
- Visualizar resultados en pantalla.
- Copiar Markdown.
- Descargar JSON.
- Descargar Markdown.
- Generar y descargar mini reporte PDF con graficas y analisis IA.
- Restringir descarga de reportes a usuarios registrados.
- Restringir funcionalidades IA a usuarios registrados o con permiso.

No incluye en MVP:

- Ejecutar ETL.
- Subir archivos.
- Ejecutar migraciones.
- Administrar Supabase.
- Administrar secretos.
- Modificar datos.

Nota: el PDF del frontend debe generarse a partir de datos ya expuestos por la API y del analisis IA ya calculado; no debe ejecutar ETL, migraciones ni modificar datos.

## 8. Pantallas propuestas

### 8.1 Reporte Ejecutivo

Contenido:

- Selector de periodo.
- Estado de API.
- Boton para generar reporte extendido.
- Resumen ejecutivo.
- Contexto de inflacion comparable.
- Analisis por familia de linea.
- Rankings por estado.
- Graficas del periodo seleccionado.
- Cruces futuros.

Graficas sugeridas:

- Monto colocado actual vs previo.
- Creditos formalizados actual vs previo.
- Ticket promedio actual vs previo.
- Variacion nominal vs real.
- Participacion por familia en monto.
- Participacion por familia en creditos.
- Top estados por monto.
- Top estados por creditos.

### 8.2 Analisis Asistido

Contenido:

- Boton para generar analisis IA.
- Tesis ejecutiva.
- Hallazgos clave.
- Lectura estatal.
- Lectura real vs nominal.
- Efecto mezcla.
- Preguntas para siguiente analisis.
- Siguientes cruces recomendados.
- Angulo para comunicacion.

### 8.3 Exportaciones

Contenido:

- Copiar Markdown.
- Descargar `mini_report_extended.json`.
- Descargar `mini_report_extended.md`.
- Descargar `ai_report.json`.
- Descargar `ai_report.md`.
- Descargar mini reporte PDF.

La descarga de PDF debe requerir usuario registrado y permiso suficiente.

### 8.4 Administracion futura

No forma parte del MVP, pero el diseno debe permitir evolucionar hacia:

- administracion de usuarios;
- roles/permisos;
- limites de consumo IA;
- auditoria de descargas;
- historial de reportes generados.

## 9. Estados UI esperados

El frontend debe manejar:

- Cargando.
- API disponible.
- API no disponible.
- Falta API key en servidor frontend.
- `401` por API key invalida.
- `422` por parametros invalidos.
- Timeout de API.
- Fallback de inflacion no disponible.
- Fallback de IA no configurada.
- Usuario no autenticado.
- Usuario sin permisos de descarga.
- Usuario sin permisos de IA.
- Limite de uso de IA alcanzado, si se define control de cuotas.
- Error controlado sin exponer stack trace.

## 10. Contrato API inicial

Parametros comunes:

```text
current_year: int
previous_year: int
month_limit: int | null
start_year: int | null
end_year: int | null
```

Endpoints a consumir:

```text
GET /health
GET /db/health
GET /mini-report/extended/json
GET /mini-report/extended/markdown
GET /mini-report/ai/json
GET /mini-report/ai/markdown
```

Headers server-side:

```text
X-API-Key: <valor seguro del entorno del frontend>
```

## 11. Graficas del frontend

Las graficas del frontend deben generarse con base en el periodo seleccionado por el usuario.

Principios:

- No recalcular metricas de negocio fuera del contrato del backend si ya existen en el JSON extendido.
- Usar el JSON extendido como fuente de datos.
- Si se requieren series adicionales no disponibles, agregarlas primero al contrato API/backend.
- No leer directamente Supabase desde el frontend.
- No consumir CSVs ni archivos locales desde el frontend.

Librerias candidatas:

- Recharts.
- ECharts.
- Visx.

Preferencia inicial:

```text
Recharts
```

Motivo: suficiente para dashboard ejecutivo, simple de integrar con React/Next.js y facil de mantener.

## 12. Mini reporte PDF

El frontend debe poder generar un mini reporte PDF que integre:

- resumen ejecutivo;
- graficas principales;
- contexto de inflacion comparable;
- analisis por familia de linea;
- lectura estatal;
- salida del analisis asistido por IA;
- metodologia y warnings.

Opcion recomendada:

```text
Generar PDF server-side en el frontend.
```

Flujo:

```text
Usuario autenticado
-> Frontend server-side
-> API backend
-> Render HTML/Markdown + graficas
-> Generacion PDF
-> Descarga controlada
```

Ventajas:

- No expone secretos.
- Permite controlar permisos antes de descargar.
- Facilita auditoria futura.
- Permite generar PDF consistente.

Riesgos:

- Requiere cuidar tiempos de render y memoria.
- Puede necesitar librerias como Playwright, Puppeteer o generador PDF server-side.

No se recomienda generar el PDF en navegador para produccion porque reduce control sobre permisos, formato y exposicion de datos.

## 13. Usuarios registrados y control de acceso

El frontend debe ser escalable hacia usuarios registrados.

Reglas:

- Usuarios no autenticados pueden ver solo una pantalla publica minima o no tener acceso.
- Usuarios autenticados pueden consultar reporte segun permisos.
- Descarga de PDF debe requerir usuario registrado.
- Funciones IA deben requerir usuario registrado y permiso explicito.
- La API key del backend no debe exponerse al usuario final.

Permisos sugeridos:

```text
viewer:
  - consultar reporte extendido
  - ver graficas

analyst:
  - consultar reporte extendido
  - ver graficas
  - usar IA
  - descargar Markdown/JSON

admin:
  - todo lo anterior
  - descargar PDF
  - administrar usuarios/configuracion futura
```

Nota: los nombres de roles son propuesta inicial. Deben ajustarse a las reglas reales de negocio antes de implementar.

Opciones de autenticacion:

- Supabase Auth.
- Auth.js / NextAuth.
- Google Identity.
- Identity-Aware Proxy si se mantiene en GCP.

Recomendacion inicial:

```text
Supabase Auth o Auth.js, segun hosting final del frontend.
```

Para un MVP interno controlado, puede iniciarse con una autenticacion simple, pero no debe publicarse sin control de acceso.

## 14. Variables de entorno del frontend

Sugeridas:

```text
INFONAVIT_API_BASE_URL=https://infonavit-strategic-report-api-490229283844.us-west1.run.app
INFONAVIT_API_KEY=...
AUTH_SECRET=...
AUTH_PROVIDER_CLIENT_ID=...
AUTH_PROVIDER_CLIENT_SECRET=...
```

Reglas:

- No versionar `.env`.
- Crear `.env.example` sin valores reales.
- En deploy, usar secretos o variables seguras del proveedor.
- No exponer `INFONAVIT_API_KEY` con prefijo publico como `NEXT_PUBLIC_`.
- No exponer secretos de autenticacion con prefijo publico.

## 15. Fases de trabajo

### Fase 0 - Preparacion

- Confirmar repo separado.
- Confirmar stack.
- Confirmar hosting objetivo.
- Confirmar si el frontend sera interno, privado o publico.
- Confirmar estrategia de secretos.
- Confirmar estrategia de usuarios/permisos.
- Confirmar si el PDF entra en MVP o en fase inmediatamente posterior.

### Fase 1 - Scaffold

- Crear repo `infonavit-strategic-report-ui`.
- Configurar TypeScript.
- Configurar Tailwind.
- Crear layout base.
- Crear cliente server-side para API backend.
- Crear `.env.example`.
- Configurar lint/test basico.
- Preparar estructura de rutas protegidas.

### Fase 2 - MVP funcional

- Formulario de periodo.
- Llamada a `/health`.
- Llamada a `/mini-report/extended/json`.
- Llamada a `/mini-report/extended/markdown`.
- Render de reporte extendido.
- Graficas basicas del periodo seleccionado.
- Copiar/descargar Markdown.

### Fase 3 - IA

- Llamada a `/mini-report/ai/json`.
- Llamada a `/mini-report/ai/markdown`.
- Render de secciones IA.
- Mostrar fallback si IA no esta configurada.
- Validar que no se expongan prompts ni secretos.
- Restringir uso de IA a usuarios con permiso.

### Fase 3.5 - PDF

- Definir plantilla del mini reporte PDF.
- Incluir graficas.
- Incluir salidas IA.
- Generar PDF server-side.
- Restringir descarga a usuarios registrados con permiso.
- Registrar errores sin exponer secretos.

### Fase 4 - Hardening

- Manejo completo de errores.
- Telemetria basica del frontend.
- Pruebas e2e ligeras.
- Revision de accesibilidad.
- Definir autenticacion si se expone a usuarios externos.
- Definir cuotas o limites de uso para IA si aplica.

### Fase 5 - Deploy

- Deploy controlado.
- Variables seguras configuradas.
- Validacion contra Cloud Run.
- Documentacion operativa.
- Monitoreo inicial.

## 16. Criterios de aceptacion del MVP

- El usuario puede seleccionar periodo.
- El usuario puede consultar el reporte extendido.
- El usuario puede consultar el analisis IA.
- El usuario puede ver graficas basadas en el periodo seleccionado.
- El usuario puede copiar Markdown.
- El usuario puede descargar JSON y Markdown.
- El usuario autorizado puede descargar mini reporte PDF.
- El frontend no expone `X-API-Key` en el navegador.
- El frontend no expone secretos de autenticacion.
- Las funcionalidades IA pueden restringirse por usuario/rol.
- Los errores se muestran de forma controlada.
- No hay escritura en backend ni base de datos.
- No se ejecutan migraciones.
- No se modifica la API actual.

## 17. Decisiones abiertas

- Crear repo separado o monorepo.
- Usar Next.js o Vite.
- Hosting: Vercel, Cloud Run, Firebase Hosting u otro.
- App interna privada o app publica.
- Requerimiento de login.
- Necesidad de auditoria de usuarios.
- Politica de costos y limites de consumo IA.
- Branding visual.
- Nivel de exportacion requerido.
- Libreria de graficas.
- Generador PDF server-side.
- Roles y permisos definitivos.
- Si PDF queda en MVP o fase 3.5.
- Proveedor de autenticacion.

## 18. Recomendacion inmediata

Avanzar con:

1. Crear repo separado `infonavit-strategic-report-ui`.
2. Usar Next.js + TypeScript + Tailwind.
3. Implementar llamadas server-side para no exponer `X-API-Key`.
4. Definir autenticacion desde el diseno, aunque se implemente de forma minima al inicio.
5. Construir MVP de consulta, graficas y exportacion.
6. Agregar PDF server-side con graficas y salida IA.
7. Mantener el backend actual como API estable de solo lectura.

Mientras tanto, continuar monitoreando Cloud Run antes de ampliar funcionalidad productiva y crear nuevos tags solo para cambios posteriores validados.
