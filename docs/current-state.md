# Estado actual del proyecto

> Última actualización: 2026-05-14

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
| **S5** | #16 #17 #18 #19 #20 | **Pendiente** | due 2026-07-04 |

---

## Issues abiertos

### Sprint 5 — milestone: "Sprint 5 - Calidad y Despliegue"

| # | Título | MoSCoW | Estimación |
|---|--------|--------|-----------|
| #16 | Tests de rendimiento con JMeter | must-have | 8 h |
| #17 | Evaluación de usabilidad SUS (≥68 puntos) | must-have | 8 h |
| #18 | Despliegue en PythonAnywhere (plan Hacker) | must-have | 8 h |
| #19 | Configuración de dominio .com | should-have | 4 h |
| #20 | Documentación técnica final (ISO/IEC 25010) | must-have | 16 h |

**Orden lógico recomendado:** #18 → #27 → #16 → #17 → #19 → #20

Razón del orden: el despliegue en PA (#18) desbloquea las pruebas con datos reales (#16, #17);
el issue #27 (mysqlclient) puede bloquear al #18 durante su ejecución;
la documentación (#20) requiere los resultados de JMeter y SUS.

### Deuda técnica abierta (sin milestone)

| # | Título | Origen | Bloquea |
|---|--------|--------|---------|
| #27 | Verificar instalación de mysqlclient en PythonAnywhere | Auditoría 2026-05-14 | #18 |
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

### R5 — Dependencia operativa #18 → #27

El issue #27 (mysqlclient en PA) no tiene milestone asignado, pero es un prerequisito
funcional del issue #18 (despliegue PA). Si mysqlclient falla al compilar en Ubuntu,
el despliegue se bloqueará sin un mensaje de error claro.

**Acción sugerida:** resolver #27 como primer paso del despliegue (#18), o antes.

---

## Limitaciones conocidas

- Sin suite de tests automatizados. Criterios de aceptación validados manualmente.
- `Mantenimiento.completado` siempre es `True` al crear — nunca se filtra en ninguna query. El campo existe pero no captura ningún estado real del negocio (no hay mantenimientos "en curso"). Dead weight hasta que se implemente ese flujo.
- Motor predictivo se recalcula en cada request (sin caché). Aceptable para el volumen esperado.
- `get_equipos_criticos()` se ejecuta en cada request autenticado de rutas `reports.*`
  (para el badge de alertas en navbar). Sin optimización de caché entre requests.
- PDFs generados síncronamente por WeasyPrint. Sin procesamiento asíncrono.
  Puede ser lento con reportes muy grandes.
- `setup_db.py` está en el repo (commit b6a33a5). Sin dependencias externas para reproducir el entorno.

---

## Próximos pasos

1. Iniciar Sprint 5 con `gh issue view 18` (despliegue PythonAnywhere).
4. Durante el despliegue, resolver y cerrar #27 (mysqlclient).
5. Con la app en PA: ejecutar pruebas JMeter (#16) y evaluación SUS (#17).
6. Configurar dominio (#19) una vez que #18 esté resuelto.
7. Redactar documentación ISO 25010 (#20) con resultados de #16 y #17.

---

## Política de mantenimiento de este archivo

Actualizar `docs/current-state.md` cuando:

- Un sprint cierra (mover fila a Completado, agregar fecha de cierre)
- Un issue cierra (actualizarlo en la tabla correspondiente)
- Se detecta una nueva inconsistencia o riesgo
- Cambia el estado funcional del sistema
- Se resuelve un riesgo o inconsistencia existente (marcarlo como cerrado)
