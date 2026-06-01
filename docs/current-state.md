# Estado actual del proyecto

> Última actualización: 2026-06-01

---

## Estado de sprints

| Sprint | Issues | Estado | Cierre |
|--------|--------|--------|--------|
| S0 | Entorno, modelos, auth, dashboard básico | Completado | 2026-04-28 |
| S1 | #2 #3 #4 #5 #6 #24 — CRUD clientes, zonas, equipos | Completado | 2026-05-01 |
| S2 | #21 #22 #7 #8 #9 #25 — Registro mantenimientos, motor predictivo base, UI | Completado | 2026-05-12 |
| S3 | #10 #11 #12 #23 #26 — Alertas críticas, dashboard global, motor refinado | Completado | 2026-05-14 |
| S4 | #13 #14 #15 — report_service, PDFs WeasyPrint | Completado | 2026-05-14 |
| Auditoría pre-S5 | Correcciones bloqueantes para PythonAnywhere | Completado | 2026-05-14 |
| **S5** | #16 #17 #18 #19 #20 #29 | **En curso** — #18 cerrado 2026-05-25, #29 cerrado 2026-05-31 | due 2026-07-04 |

---

## Issues abiertos

### Sprint 5 — milestone: "Sprint 5 - Calidad y Despliegue"

| # | Título | MoSCoW | Estimación | Estado |
|---|--------|--------|-----------|--------|
| #18 | Despliegue en PythonAnywhere (plan Developer) | must-have | 8 h | **Cerrado** 2026-05-25 |
| #29 | Listado, edición y anulación de mantenimientos | must-have | 12 h | **Cerrado** 2026-05-31 |
| #16 | Tests de rendimiento con JMeter | must-have | 8 h | **En progreso** — 3 optimizaciones aplicadas (29x dashboard, 6x PDF). PDF y dashboard concurrente quedan en #30 |
| #17 | Evaluación de usabilidad SUS (≥68 puntos) | must-have | 8 h | Abierto |
| #19 | Configuración de dominio .com | should-have | 4 h | Abierto |
| #20 | Documentación técnica final (ISO/IEC 25010) | must-have | 16 h | Abierto |

App desplegada en: https://dordonezm2.pythonanywhere.com/ (plan Developer)

**Orden lógico restante:** #16 → #17 → #19 → #20

### Deuda técnica abierta (sin milestone)

| # | Título | Origen | Bloquea |
|---|--------|--------|---------|
| ~~#27~~ | ~~Verificar instalación de mysqlclient en PythonAnywhere~~ | Auditoría 2026-05-14 | **Cerrado** 2026-05-31 — mysqlclient 2.2.8 funciona sin cambios en PA |
| #28 | Mejorar diseño páginas de error 404/500 | Auditoría 2026-05-14 | — |
| #30 | Optimizar dashboard bajo carga y generación PDF en PA | JMeter p4 (2026-06-01) | Cierre completo de #16 |

---

## Qué hace el sistema hoy

Funcionalidad completamente implementada y funcionando en desarrollo:

- Autenticación: login/logout con bloqueo por intentos fallidos
- CRUD completo: clientes, zonas, equipos instalados, tipos de equipo, componentes
- Registro de mantenimientos (transacción atómica, motor predictivo integrado al guardar)
- Motor predictivo: proyección de vencimientos por componente, algoritmo histórico/nominal
- Dashboard global: resumen de vencidos/próximos, filtro por zona
- Vista de equipos críticos: filtros zona/urgencia, accordion inline
- Badge de alertas en navbar (cuenta equipos vencidos en rutas `reports.*`)
- Reportes PDF por zona (diario con resumen) y por cliente (historial + proyección)
- Páginas de error 404/500/403 personalizadas
- Entry point WSGI (`wsgi.py`) para PythonAnywhere
- Validación de variables de entorno al arrancar en modo producción
- Listado global de mantenimientos con filtros por cliente y fechas (roles admin)
- Edición completa de mantenimientos con recálculo del motor predictivo
- Anulación de mantenimientos con motivo (soft delete — excluidos de motor predictivo y PDFs)

---

## Deuda técnica conocida

| Ref | Descripción | Severidad | Estado |
|-----|-------------|-----------|--------|
| #27 | `mysqlclient` puede fallar al compilar en Ubuntu. Alternativa: PyMySQL puro-Python | Bloqueante para deploy | Issue abierto |
| #28 | Templates 404/500 son mínimas (solo texto básico) | Cosmético | Issue abierto |
| — | `setup_db.py` versionado en el repo (commit b6a33a5) con SQLAlchemy 2.0 + stamp head | Resuelto | — |
| — | No hay suite de tests automatizados | Deuda S5 | Cubierto por #16/#17 |

---

## Riesgos e inconsistencias detectadas

### ~~R1 — setup_db.py: estado ambiguo~~ — RESUELTO

El commit `b6a33a5` removió `setup_db.py` de `.gitignore` y lo añadió al repo (77 líneas,
con SQLAlchemy 2.0 + instrucción `flask db stamp head`). El archivo está versionado.
El impedimento documentado en el daily de auditoría fue resuelto en ese mismo commit.

### ~~R2 — README.md desactualizado~~ — RESUELTO

Sprint 4 corregido a "Completado" en `README.md`.

### R3 — CLAUDE.md no versionado

`CLAUDE.md` (instrucciones operativas para Claude Code) está en `.gitignore`.
Agentes que clonen el repo desde cero no tendrán ese archivo.
`AGENTS.md` y `docs/` son la única fuente de contexto persistente versionada en git.

**Consecuencia:** si las reglas de `CLAUDE.md` cambian, deben reflejarse también en
`AGENTS.md` para que no se pierdan.

### R4 — wsgi.py: instrucciones de instalación inicial vs flask db upgrade

`wsgi.py` documenta en el paso 5: "Para cambios de esquema futuros: `flask db migrate`
+ `flask db upgrade`". Esto es correcto para cambios posteriores, pero podría confundirse
con la instalación inicial donde el flujo correcto es `setup_db.py → flask db stamp head`.

**Impacto:** riesgo de que un operador ejecute `flask db upgrade` en una BD vacía en PA
y obtenga errores. La documentación en `wsgi.py` debería aclarar que el paso 4 es solo
para instalación inicial.

### ~~R5 — Dependencia operativa #18 → #27~~ — RESUELTO

#27 cerrado 2026-05-31: mysqlclient 2.2.8 funciona sin cambios en PA. #18 cerrado 2026-05-25.

### ~~R6 — get_equipos_criticos() ejecuta dos veces por request~~ — RESUELTO 2026-06-01

Detectado mediante JMeter el 2026-06-01. Resuelto con tres commits en cadena:

1. `02073f7` — Cachear `get_equipos_criticos()` en `flask.g`.
2. `463dfc1` — Batch del historial de reemplazos en una sola query (`_get_historial_reemplazos_map`).
3. `7ca4fed` — Skip de `get_equipos_criticos()` en context_processor para endpoints PDF.

Mejora en PA (2.000 equipos, plan Developer):

| Endpoint | Antes | Después (p4) | Mejora |
|---|---|---|---|
| GET /reports/dashboard | 59.566 ms (timeout) | 1.911 ms (mean), 1.917 ms (median) | **31x** |
| GET /reports/zona/1/pdf | 55.611 ms (timeout) | 8.845 ms (mean) | **6.3x** |

Resultados en `watermax-notas/sprints/sprint5/jmeter/resultados/p4/`.

Optimización pendiente trasladada al issue #30:
- Dashboard p99 bajo 4-concurrent excede 2 s (max 2.748 ms).
- PDF ≥ 5 s en todos los samples (CPU-bound de WeasyPrint).

---

## Limitaciones conocidas

- Sin suite de tests automatizados. Criterios de aceptación validados manualmente.
- `Mantenimiento.completado` siempre es `True` al crear — nunca se filtra en ninguna query. El campo existe pero no captura ningún estado real del negocio (no hay mantenimientos "en curso"). Dead weight hasta que se implemente ese flujo.
- Motor predictivo: `get_equipos_criticos()` itera 2.000 equipos en memoria por request.
  Tras optimizaciones del 2026-06-01 (commits `02073f7`, `463dfc1`, `7ca4fed`) ejecuta
  1 query SQL en lugar de ~20.000. Aceptable para volumen actual en PA Developer.
  Pendiente: max p99 bajo 4-concurrent llega a 2.7 s (criterio #16 era ≤ 2 s). Ver #30.
- PDFs generados síncronamente por WeasyPrint. En PA Developer 8-12 s por reporte de
  50 equipos (CPU-bound). Criterio #16 era ≤ 5 s. Sin caché ni asincronía. Ver #30.
- `setup_db.py` está en el repo (commit b6a33a5). Sin dependencias externas para reproducir el entorno.

---

## Próximos pasos

1. **#16:** decisión de cierre pendiente — pasan criterios 1, 4 y 5; criterio 2 (dashboard)
   cumple en mediana pero no en p99 bajo carga; criterio 3 (PDF) no cumple. Trabajo
   restante movido a #30. Sesión cerrada el 2026-06-01 sin cerrar #16.
2. **#30:** profilar y optimizar dashboard concurrente + PDF.
3. **#17:** evaluación SUS con usuarios reales (≥ 68 puntos).
4. **#19:** configurar dominio .com.
5. **#20:** redactar documentación ISO 25010 con resultados de #16 y #17.

---

## Política de mantenimiento de este archivo

Actualizar `docs/current-state.md` cuando:

- Un sprint cierra (mover fila a Completado, agregar fecha de cierre)
- Un issue cierra (actualizarlo en la tabla correspondiente)
- Se detecta una nueva inconsistencia o riesgo
- Cambia el estado funcional del sistema
- Se resuelve un riesgo o inconsistencia existente (marcarlo como cerrado)
