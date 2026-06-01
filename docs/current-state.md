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
| **S5** | #16 #17 #18 #19 #20 | **En curso** — #18 cerrado 2026-05-25 | due 2026-07-04 |

---

## Issues abiertos

### Sprint 5 — milestone: "Sprint 5 - Calidad y Despliegue"

| # | Título | MoSCoW | Estimación | Estado |
|---|--------|--------|-----------|--------|
| #18 | Despliegue en PythonAnywhere (plan Developer) | must-have | 8 h | **Cerrado** 2026-05-25 |
| #16 | Tests de rendimiento con JMeter | must-have | 8 h | **En progreso** — plan ejecutado, criterios pendientes (ver R6) |
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

### R6 — get_equipos_criticos() ejecuta dos veces por request — BLOQUEANTE para #16

Detectado mediante JMeter el 2026-06-01. El context_processor que dibuja el badge de
alertas en navbar llama a `get_equipos_criticos()` en cada request de rutas `reports.*`,
igual que las views que lo usan (dashboard, criticos). Con 2.000 equipos activos en PA:
~20.000 queries por request → dashboard tarda ~60 s → timeout en JMeter.

Resultados del run completo (PA, 2026-06-01):
- `GET /reports/dashboard`: Average 59.566 ms, Error 100% (criterio: ≤ 2.000 ms)
- `GET /reports/zona/1/pdf`: Average 55.611 ms, Error 100% (criterio: ≤ 5.000 ms)

**Fix pendiente:** cachear resultado en `flask.g` dentro de `get_equipos_criticos()`.
El context_processor reutilizará el valor ya calculado por la view en el mismo request.

---

## Limitaciones conocidas

- Sin suite de tests automatizados. Criterios de aceptación validados manualmente.
- `Mantenimiento.completado` siempre es `True` al crear — nunca se filtra en ninguna query. El campo existe pero no captura ningún estado real del negocio (no hay mantenimientos "en curso"). Dead weight hasta que se implemente ese flujo.
- Motor predictivo se recalcula en cada request (sin caché). Aceptable para el volumen esperado.
- `get_equipos_criticos()` se ejecuta **dos veces** por request en rutas `reports.*`:
  una en la view (dashboard/criticos) y otra en el context_processor del badge de navbar.
  Con 2.000 equipos activos genera ~20.000 queries por request. Medido en JMeter (#16):
  dashboard tarda ~60 s en PA → criterio ≤ 2 s no cumplido. Pendiente cachear con `flask.g`.
- PDFs generados síncronamente por WeasyPrint. Sin procesamiento asíncrono.
  Puede ser lento con reportes muy grandes.
- `setup_db.py` está en el repo (commit b6a33a5). Sin dependencias externas para reproducir el entorno.

---

## Próximos pasos

1. **#16 (bloqueante):** cachear `get_equipos_criticos()` en `flask.g`, re-correr JMeter
   en modo no-GUI y verificar criterios ≤ 2 s (dashboard) y ≤ 5 s (PDF). Cerrar issue.
2. **#17:** evaluación SUS con usuarios reales (≥ 68 puntos).
3. **#19:** configurar dominio .com.
4. **#20:** redactar documentación ISO 25010 con resultados de #16 y #17.

---

## Política de mantenimiento de este archivo

Actualizar `docs/current-state.md` cuando:

- Un sprint cierra (mover fila a Completado, agregar fecha de cierre)
- Un issue cierra (actualizarlo en la tabla correspondiente)
- Se detecta una nueva inconsistencia o riesgo
- Cambia el estado funcional del sistema
- Se resuelve un riesgo o inconsistencia existente (marcarlo como cerrado)
