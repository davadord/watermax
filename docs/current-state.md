# Estado actual del proyecto

> Última actualización: 2026-07-26

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
| **S5** | #16 #17 #18 #19 #20 #29 #31 #32 #33 | **Completado** — todos los issues de milestone cerrados | 2026-07-26 |

**Fase activa: preparación de la sustentación oral.** El código de sprint está cerrado; el documento de titulación (`ORDONEZ_MENDIETA_DAVID_ADRIAN_PT_SISTEMAS.md/.docx`) y el material de defensa están en `watermax-notas`.

---

## Issues del milestone Sprint 5 — TODOS CERRADOS

| # | Título | MoSCoW | Estado |
|---|--------|--------|--------|
| #18 | Despliegue en PythonAnywhere (plan Developer) | must-have | **Cerrado** 2026-05-25 |
| #29 | Listado, edición y anulación de mantenimientos | must-have | **Cerrado** 2026-05-31 |
| #16 | Tests de rendimiento con JMeter | must-have | **Cerrado** 2026-06-01 — 5/5 criterios cumplen en PA (p7/p7b). Dashboard y PDF resueltos vía #30 |
| #31 | Suite de pruebas unitarias — motor predictivo + modelo Usuario | must-have | **Cerrado** 2026-06-02 — 34 pruebas pytest |
| #32 | Suite de pruebas unitarias — CRUD gestión usuarios | must-have | **Cerrado** 2026-06-05 — 17 pruebas pytest (51 total) |
| #33 | Perfil de usuario (RF-04) + refactor de suite a pruebas unitarias puras | must-have | **Cerrado** 2026-07-08 — 65/65 pruebas, 100% unitarias, 88% cobertura en módulos críticos |
| #17 | Evaluación de usabilidad SUS (≥68 puntos) | must-have | **Cerrado** 2026-07-23 — media 85.0 ("Bueno"), 4 evaluadores reales |
| #19 | Configuración de dominio .com | should-have | **Cerrado** 2026-07-23 — alcance reducido: se queda en pre-producción con subdominio PythonAnywhere (HTTPS válido), sin dominio propio |
| #20 | Documentación técnica final (ISO/IEC 25010) | must-have | **Cerrado** 2026-07-26 — PT completo con ISO 25010, UML, JMeter+SUS, LOPDP y ADR (docs/decisions.md) |

App desplegada en: https://dordonezm2.pythonanywhere.com/ (plan Developer, pre-producción)

### Deuda técnica — cerrada 2026-07-26

| # | Título | Origen | Resolución |
|---|--------|--------|---------|
| ~~#27~~ | ~~Verificar instalación de mysqlclient en PythonAnywhere~~ | Auditoría 2026-05-14 | **Cerrado** 2026-05-31 — mysqlclient 2.2.8 funciona sin cambios en PA |
| ~~#28~~ | ~~Mejorar diseño páginas de error 404/500~~ | Auditoría 2026-05-14 | **Cerrado** 2026-07-26 — errors/404.html con diseño completo, navbar protegido para anónimos, rollback en handler 500 |
| ~~#30~~ | ~~Optimizar dashboard bajo carga y generación PDF en PA~~ | JMeter p4 (2026-06-01) | **Cerrado** 2026-06-01 — C1 y C2 cumplen en PA (p7/p7b). D16 reportlab + D17 caché resumen global |
| ~~#34~~ | ~~Buscador y paginación en listado de clientes~~ | Auditoría UX (500 equipos) | **Cerrado** 2026-07-26 — resuelto en commit 5e1faa7 (2026-07-23) |
| ~~#35~~ | ~~Buscador y paginación en listado de equipos~~ | Auditoría UX (500 equipos) | **Cerrado** 2026-07-26 — resuelto en commit 5e1faa7 (2026-07-23) |
| ~~#36~~ | ~~Reemplazar select por buscador (autocomplete)~~ | Auditoría UX (500 equipos) | **Cerrado** 2026-07-26 — componente client_picker, commit 5e1faa7 |
| ~~#37~~ | ~~Alta rápida de mantenimiento~~ | Pedido del tutor | **Cerrado** 2026-07-26 — vista /maintenance/nuevo, commit 5e1faa7 |
| ~~#38~~ | ~~Propagar filtro de zona dashboard↔reportes~~ | Auditoría UX | **Cerrado** 2026-07-26 — dashboard ya propaga zona_id a componentes_cambiados, commit 5e1faa7 |

---

## Qué hace el sistema hoy

Funcionalidad completamente implementada y funcionando en desarrollo:

- Autenticación: login/logout con bloqueo por intentos fallidos
- Perfil de usuario: cambio de contraseña propia (RF-04), hash bcrypt
- CRUD completo: clientes, zonas, equipos instalados, tipos de equipo, componentes
- Gestión de usuarios: alta, edición y desactivación con control de roles (propietario no editable por administrativo; nadie puede desactivarse a sí mismo)
- Registro de mantenimientos (transacción atómica, motor predictivo integrado al guardar)
- Motor predictivo: proyección de vencimientos por componente, algoritmo histórico/nominal
- Dashboard global: resumen de vencidos/próximos, filtro por zona
- Vista de equipos críticos: filtros zona/urgencia, accordion inline
- Badge de alertas en navbar (cuenta equipos vencidos en rutas `reports.*`)
- Reportes PDF por zona (diario con resumen, orientación horizontal) y por cliente (historial + proyección)
- Reportes con filtros de estado/fecha/cliente
- Páginas de error 404/500/403 personalizadas
- Entry point WSGI (`wsgi.py`) para PythonAnywhere
- Validación de variables de entorno al arrancar en modo producción
- Listado global de mantenimientos con filtros por cliente y fechas (roles admin)
- Edición completa de mantenimientos con recálculo del motor predictivo
- Anulación de mantenimientos con motivo (soft delete vía `motivo_anulacion` — excluidos de motor predictivo y PDFs)
- Suite de pruebas: 65 casos, 100% unitarios (sin HTTP), 88% cobertura en módulos críticos

---

## Deuda técnica conocida

Toda la deuda técnica identificada durante el proyecto está cerrada (ver tabla de arriba: #27, #28, #30, #34-#38).

| Ref | Descripción | Severidad | Estado |
|-----|-------------|-----------|--------|
| — | `setup_db.py` versionado en el repo (commit b6a33a5) con SQLAlchemy 2.0 + stamp head | Resuelto | — |
| — | Suite de tests: 65 pruebas 100% unitarias (pytest) — motor predictivo, CRUD usuarios, auth, perfil | Resuelto | #31 + #32 + #33 cerrados |

---

## Riesgos e inconsistencias detectadas

### ~~R1 — setup_db.py: estado ambiguo~~ — RESUELTO

El commit `b6a33a5` removió `setup_db.py` de `.gitignore` y lo añadió al repo (77 líneas,
con SQLAlchemy 2.0 + instrucción `flask db stamp head`). El archivo está versionado.
El impedimento documentado en el daily de auditoría fue resuelto en ese mismo commit.

### ~~R2 — README.md desactualizado~~ — RESUELTO

Sprint 4 corregido a "Completado" en `README.md`.

### R3 — Configuración local no versionada

Los archivos de configuración de entorno de desarrollo están en `.gitignore`.
`AGENTS.md` y `docs/` son la única fuente de contexto persistente versionada en git.

**Consecuencia:** cualquier regla operativa local debe reflejarse en `AGENTS.md`
para que no se pierda al clonar el repositorio.

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
  El dashboard concurrente (max bajo 4-5 usuarios) llegaba a 2.7-3.9 s (criterio #16
  C1 era ≤ 2 s). Resuelto con caché cross-request del resumen global (#30, D17):
  el panorama se calcula una vez y se comparte (local: cold 194 ms → warm ~0 ms),
  con TTL 60 s + invalidación en escritura + lock single-flight. **Confirmado en PA:
  JMeter p7/p7b → dashboard max 1.460/456 ms, 0 fallos de assertion.**
- PDF por zona migrado a reportlab (#30, D16): render local 1228→244 ms (5.0x).
  **Confirmado en PA (p6→p7): 8.845 → 1.353 ms mean, consistente < 5 s.** El PDF por
  cliente sigue en WeasyPrint. Antes de la migración: WeasyPrint 8-12 s en PA Developer
  (CPU-bound), no cumplía el criterio #16 ≤ 5 s.
- `setup_db.py` está en el repo (commit b6a33a5). Sin dependencias externas para reproducir el entorno.

---

## Próximos pasos

Sprint 5 completado — no quedan issues de código pendientes. Próximo hito: sustentación oral (ver `watermax-notas/sustentacion/`).

---

## Política de mantenimiento de este archivo

Actualizar `docs/current-state.md` cuando:

- Un sprint cierra (mover fila a Completado, agregar fecha de cierre)
- Un issue cierra (actualizarlo en la tabla correspondiente)
- Se detecta una nueva inconsistencia o riesgo
- Cambia el estado funcional del sistema
- Se resuelve un riesgo o inconsistencia existente (marcarlo como cerrado)
