# Decisiones técnicas y de producto

Registro de decisiones ya tomadas. Antes de cambiar cualquiera, leer la razón.
"[issue]" indica que la decisión surgió o fue documentada en ese issue.
"[auditoría]" indica que surgió en la sesión de auditoría pre-Sprint 5 (2026-05-14).
"[práctica observada]" indica que se infirió del código/historia sin estar escrita formalmente.

---

## D1 — zona_id en EquipoInstalado, no en Cliente

**Decisión:** `EquipoInstalado.zona_id` es la única FK de zona. `Cliente` no tiene zona.

**Razón:** Un cliente puede tener equipos en múltiples zonas. La zona es una propiedad
de la instalación física, no del cliente (persona/empresa). Filtrar por zona significa
filtrar equipos, no clientes.

**Impacto en código:** Dashboard y reportes filtran `EquipoInstalado.zona_id`. No hay
`Cliente.zona_id` en ningún modelo.

**Alternativa descartada:** zona en Cliente. Descartada porque un cliente real puede tener
locales en varias zonas de cobertura.

---

## D2 — intervalo_nominal en Componente, no en TipoEquipoComponente

**Decisión:** `Componente.intervalo_nominal` (Integer, meses enteros) vive en `Componente`,
no en la tabla de unión `TipoEquipoComponente`.

**Razón:** El intervalo de cambio es una propiedad intrínseca del componente (ej: un filtro UV
se cambia cada 12 meses independientemente del equipo en que esté). Ponerlo en la unión
requeriría duplicar el valor por cada tipo de equipo que use ese componente.

**Alternativa descartada:** intervalo por combinación tipo_equipo+componente (más flexible).
Descartada por no ser necesaria en el alcance del proyecto y añadir complejidad sin beneficio.

---

## D3 — Solo "reemplazo" resetea el reloj predictivo

**Decisión:** Solo `accion == "reemplazo"` genera `proximo_mantenimiento` y cuenta en el
historial del motor predictivo. `limpieza` y `revision` dejan `proximo_mantenimiento = NULL`.

**Razón:** El ciclo de vida del componente se mide por reemplazos físicos completos.
Una limpieza no detiene el desgaste del componente; no tiene sentido reiniciar el reloj.

**Impacto en código:**
- `_intervalo_efectivo()` filtra `DetalleMantenimiento.accion == "reemplazo"` en la query.
- `calcular_proximo_componente()` solo se llama en `maintenance.py` si `accion == "reemplazo"`.
- `DetalleMantenimiento.proximo_mantenimiento` puede ser NULL para limpiezas y revisiones.

---

## D4 — Motor predictivo: histórico vs nominal con umbral 50%

**Decisión:** Si hay ≥ 2 ciclos de reemplazo y la desviación del promedio respecto al nominal
es ≤ 50%, se usa el promedio histórico (`fuente="historico"`). Si no, se usa el nominal.

**Razón:** El intervalo nominal es una estimación del fabricante. El histórico refleja las
condiciones reales de uso del equipo. Sin embargo, si el histórico difiere más del 50% del
nominal, probablemente hay datos anómalos (mantenimientos correctivos no planificados,
equipo fuera de uso) y no es confiable como base de proyección.

**Umbral 15 días (`UMBRAL_ALERTA_DIAS`):** constante nombrada en `prediction_service.py`.
Componentes con ≤ 15 días para vencer se marcan como `proximo`.

**Guarda ZeroDivision:** `_intervalo_efectivo()` evalúa `intervalo_nominal > 0` antes de
calcular la desviación. Si `intervalo_nominal == 0`, cae a `"nominal"` directamente.

---

## D5 — SQLAlchemy 2.0 API exclusiva

**Decisión:** Todo acceso a la BD usa `select() + db.session.execute().scalars()` y
`db.session.get(Modelo, id)`. La API legacy `.query` está prohibida en el proyecto.

**Razón:** SQLAlchemy 2.0 deprecó `.query`. La app corre sobre SQLAlchemy 2.0 y
mantener consistencia evita bugs difíciles de diagnosticar por mezcla de APIs.

**Historia [auditoría]:** En la auditoría pre-Sprint 5 (2026-05-14, commit `40eb1ec`) se
migraron 25 usos de `.query` legacy en `admin.py`, `auth.py`, `reports.py` y
`prediction_service.py`. Antes de eso, `get_equipos_criticos()` todavía usaba `EquipoInstalado.query`.

---

## D6 — WeasyPrint 68.1 con import lazy y try/except

**Decisión:** `from weasyprint import HTML` se importa dentro de cada función de ruta PDF.
Cada generación de PDF está envuelta en `try/except Exception → abort(503)`.

**Razón del import lazy:** En entornos sin GTK instalado, el import al nivel de módulo
falla al arrancar la app. Con import lazy, la app arranca normalmente y solo falla cuando
se intenta generar un PDF, donde el `abort(503)` lo maneja gracefully.

**Razón de la versión 68.1:** WeasyPrint fue actualizado de 62.3 a 68.1 en Sprint 4
para corregir un bug en `super().transform`. [#13]

**Razón del try/except:** Si GTK no está disponible en producción (o WeasyPrint falla
por cualquier causa), el usuario recibe un 503 explícito en vez de un 500 genérico.

---

## D7 — Estructura de dos repositorios (watermax vs watermax-notas)

**Decisión:** El código vive en `watermax`. Los dailies Scrum, teoría y notas personales
viven en `watermax-notas` (repo separado, privado).

**Razón:** El material de aprendizaje y proceso es personal, no forma parte del entregable
técnico. El historial de git del proyecto de código debe reflejar solo cambios funcionales.
`sprints/`, `teoria/` y `CLAUDE.md` están en `.gitignore` de `watermax`.

**Ruta local watermax-notas:**
`D:\davadord\Escritorio\TITULACION\ANTEPROYECTO\PROTOTIPO\watermax-sprint0\watermax-notas`

**[práctica observada]**

---

## D8 — ProductionConfig sin fallback en SECRET_KEY y DATABASE_URL

**Decisión:** `ProductionConfig.SECRET_KEY = os.environ.get("SECRET_KEY")` (sin valor por
defecto). `create_app("production")` lanza `RuntimeError` si alguna var crítica falta.

**Razón:** Un `SECRET_KEY` hardcodeado o predecible en producción permite forjar cookies
de sesión (ataque de session forgery). La app debe fallar ruidosamente, no silenciosamente,
si las vars de entorno de seguridad no están configuradas.

**Historia [auditoría]:** El fallback genérico en `ProductionConfig` fue eliminado en la
auditoría pre-Sprint 5 (2026-05-14).

---

## D9 — bcrypt para contraseñas de usuario

**Decisión:** Las contraseñas se hashean con bcrypt (`py-bcrypt`), no con `werkzeug.security`.

**Razón:** bcrypt incluye salt automático y cost factor ajustable, haciendo los hashes
resistentes a ataques de fuerza bruta. Es la opción recomendada para contraseñas de usuario.
`werkzeug.security` usa PBKDF2 que también es seguro, pero bcrypt es preferido para passwords.

**[práctica observada]**

---

## D10 — Inicialización de BD: setup_db.py + stamp head (no db.upgrade en blanco)

**Decisión:** En un servidor nuevo, la secuencia es `python setup_db.py` →
`flask db stamp head`. No se usa `flask db upgrade` para instalación inicial.

**Razón:** La cadena de migraciones Alembic aplica *deltas* a un schema existente. No puede
crear el schema completo desde cero de forma confiable. `db.create_all()` (en `setup_db.py`)
crea todas las tablas directamente desde los modelos actuales. Luego `flask db stamp head`
marca todas las migraciones como aplicadas sin ejecutarlas.

**Riesgo conocido:** `setup_db.py` está en `.gitignore`. Si se regenera el entorno,
el operador debe tener acceso a la copia local actualizada. Ver R1 en `docs/current-state.md`.

**[auditoría]**

---

## D11 — Flujo guiado para crear equipo desde cliente

**Decisión:** La ruta `/admin/equipos/nuevo` acepta `?cliente_id=X`. Con ese parámetro,
el formulario muestra el cliente como texto fijo + `<input hidden>`. Sin parámetro (o con
cliente inactivo), muestra el select completo.

**Razón:** Mejora de UX para el flujo más común: el operador ya está en la ficha de un
cliente y quiere agregar un equipo. Evita selección manual del cliente.

**Rutas relacionadas:** botón "Agregar equipo" en `/admin/clientes` (por fila),
`empty_state` en `/maintenance/cliente/<id>` también pasa `cliente_id`. [#26]

---

## D12 — Commits sin referencia a herramientas de IA

**Decisión:** Los mensajes de commit no incluyen `Co-Authored-By: Claude`, referencias
a herramientas de IA ni texto autogenerado por modelos.

**Razón:** El proyecto es un trabajo académico de titulación. El historial de git debe
reflejar el trabajo del autor para la defensa y evaluación.

---

## D13 — @login_required antes de @role_required (orden de decoradores)

**Decisión:** El orden es siempre `@login_required` primero, luego `@role_required`.

**Razón técnica:** Los decoradores en Python se aplican de abajo hacia arriba en la definición
pero de afuera hacia adentro en la ejecución. Con este orden, si el usuario no está
autenticado, Flask-Login redirige al login antes de que `role_required` intente leer
`current_user.rol` (que sería inválido para un usuario anónimo).

**[práctica observada]**

---

## D14 — proximo_mantenimiento en DetalleMantenimiento (no en EquipoInstalado)

**Decisión:** La fecha de próximo mantenimiento se guarda por componente y por intervención
(`DetalleMantenimiento.proximo_mantenimiento`), no a nivel de equipo.

**Razón:** Cada componente de un equipo tiene su propio ciclo de vencimiento independiente.
Un equipo puede tener un componente vencido y otro en plazo. Guardar una sola fecha por
equipo perdería esta granularidad.

**Impacto:** El motor predictivo recalcula en tiempo real (no lee `proximo_mantenimiento`
del campo). El campo `proximo_mantenimiento` queda como referencia histórica y podría
usarse para optimizaciones futuras de consulta (está indexado).

---

## D15 — Badge de alertas solo en rutas reports.*

**Decisión:** `alertas_count` en el context processor solo llama a `get_equipos_criticos()`
cuando `request.endpoint` empieza con `"reports."`.

**Razón:** `get_equipos_criticos()` carga todos los equipos activos con joinedload y luego
recalcula vencimientos. Ejecutarlo en cada request de toda la app sería costoso.
El badge de alertas solo es relevante en el módulo de reportes.

**[práctica observada, inferido del código]**

---

## D16 — Motor del PDF de zona: reportlab (no WeasyPrint)

**Decisión:** El reporte por zona (`/reports/zona/<id>/pdf`) se genera con **reportlab**
(Platypus) en `report_service.build_reporte_zona_pdf(datos)`, sin template HTML.
El reporte por cliente sigue en WeasyPrint. Ambos motores conviven.

**Razón:** El criterio de rendimiento de #16 exige PDF mean ≤ 5000 ms en PythonAnywhere
Developer. El profiling con cProfile (#30) mostró que el render del reporte de zona era
**98.5% WeasyPrint `write_pdf`** (motor de layout CSS, CPU-bound): 216k llamadas a
`css/__missing__`, 376k a `check_math`. En PA Developer eso daba 8–13 s single-user;
incluso aplanando todo el HTML (experimento H1b) no bajaba cómodo de 5 s. WeasyPrint es
estructuralmente incapaz de cumplir C2 en ese hardware manteniendo el contenido requerido.

reportlab usa layout imperativo (sin motor CSS): en la misma máquina y con la misma BD
(zona 1, 50 equipos) el render bajó de **1228 ms → 244 ms (5.0x)**, proyectando ~1.7–2.9 s
en PA. Además, al liberar rápido los 2-3 workers de PA, reduce la contención que degradaba
el dashboard concurrente (causa raíz compartida documentada en current-state.md R6/#30).

**Por qué desviarse del anteproyecto (WeasyPrint):** que la aplicación CUMPLA su criterio
de calidad es un resultado más fuerte para la defensa que documentar un límite. Decisión
tomada con el autor el 2026-06-01.

**Alternativas descartadas:**
- *Mantener WeasyPrint y documentar el límite:* no cumple C2; deja el criterio #16 abierto.
- *Generación asíncrona (cola/worker):* PA Developer no ofrece workers de fondo en el plan;
  añade infraestructura fuera del alcance de Sprint 5.

**Impacto en código:**
- `report_service.build_reporte_zona_pdf(datos)`: import reportlab lazy (igual que la regla
  WeasyPrint en AGENTS.md), envuelto en `try/except → abort(503)` en la ruta.
- Texto dinámico (clientes, componentes, series) escapado con `xml.sax.saxutils.escape`
  antes de insertarlo en el markup de `Paragraph` (un `&` o `<` sin escapar rompe el parse).
- Template `reports/pdf_zona.html` eliminado (huérfano).
- `requirements.txt`: + `reportlab==4.5.1`. WeasyPrint permanece (lo usa el PDF de cliente).
