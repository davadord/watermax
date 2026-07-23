from datetime import date
from io import BytesIO
from xml.sax.saxutils import escape
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload
from app import db
from app.models.client import Zona, Cliente
from app.models.equipment import EquipoInstalado, TipoEquipo, TipoEquipoComponente, Componente
from app.models.maintenance import Mantenimiento, DetalleMantenimiento
from app.services.prediction_service import (
    calcular_vencimientos, URGENCIA_VENCIDO, URGENCIA_PROXIMO, URGENCIA_EN_PLAZO,
)

ESTADOS_POR_FILTRO = {
    "vencido": (URGENCIA_VENCIDO,),
    "proximo": (URGENCIA_PROXIMO,),
    "en_plazo": (URGENCIA_EN_PLAZO,),
    "criticos": (URGENCIA_VENCIDO, URGENCIA_PROXIMO),
}


def get_reporte_zona(zona_id: int, fecha=None, estado=None) -> dict:
    zona = db.session.get(Zona, zona_id)

    stmt = (
        select(EquipoInstalado)
        .where(
            EquipoInstalado.zona_id == zona_id,
            EquipoInstalado.activo == True,
        )
        .options(
            joinedload(EquipoInstalado.cliente),
            joinedload(EquipoInstalado.tipo_equipo)
                .joinedload(TipoEquipo.componentes)
                .joinedload(TipoEquipoComponente.componente),
        )
        .order_by(EquipoInstalado.id)
    )
    equipos = db.session.execute(stmt).scalars().unique().all()

    fecha_ref = fecha or date.today()
    urgencias_filtro = ESTADOS_POR_FILTRO.get(estado)
    items = []
    resumen = {"total": 0, "vencidos": 0, "proximos": 0, "en_plazo": 0}

    for equipo in equipos:
        vencimientos = calcular_vencimientos(equipo, fecha_ref=fecha_ref)
        n_vencidos = sum(1 for v in vencimientos if v["urgencia"] == URGENCIA_VENCIDO)
        n_proximos = sum(1 for v in vencimientos if v["urgencia"] == URGENCIA_PROXIMO)

        resumen["total"] += 1
        if n_vencidos:
            resumen["vencidos"] += 1
        elif n_proximos:
            resumen["proximos"] += 1
        else:
            resumen["en_plazo"] += 1

        if urgencias_filtro is not None:
            vencimientos = [v for v in vencimientos if v["urgencia"] in urgencias_filtro]
            if not vencimientos:
                continue

        items.append({
            "equipo": equipo,
            "vencimientos": vencimientos,
            "n_vencidos": n_vencidos,
            "n_proximos": n_proximos,
        })

    items.sort(key=lambda x: (-x["n_vencidos"], -x["n_proximos"]))

    return {
        "zona": zona,
        "items": items,
        "resumen": resumen,
        "fecha_ref": fecha_ref,
        "fecha_generacion": date.today(),
        "estado": estado,
    }


def get_reporte_cliente(cliente_id: int, equipo_id=None, desde=None, hasta=None) -> dict:
    cliente = db.session.get(Cliente, cliente_id)

    stmt = (
        select(EquipoInstalado)
        .where(
            EquipoInstalado.cliente_id == cliente_id,
            EquipoInstalado.activo == True,
        )
        .options(
            joinedload(EquipoInstalado.zona),
            joinedload(EquipoInstalado.tipo_equipo)
                .joinedload(TipoEquipo.componentes)
                .joinedload(TipoEquipoComponente.componente),
        )
    )
    if equipo_id:
        stmt = stmt.where(EquipoInstalado.id == equipo_id)
    equipos = db.session.execute(stmt).scalars().unique().all()

    items = []
    for equipo in equipos:
        hist_stmt = (
            select(Mantenimiento)
            .where(
                Mantenimiento.equipo_id == equipo.id,
                Mantenimiento.completado == True,
                Mantenimiento.motivo_anulacion == None,
            )
            .options(
                joinedload(Mantenimiento.detalles)
                    .joinedload(DetalleMantenimiento.componente),
                joinedload(Mantenimiento.tecnico),
            )
            .order_by(Mantenimiento.fecha.desc())
        )
        if desde:
            hist_stmt = hist_stmt.where(Mantenimiento.fecha >= desde)
        if hasta:
            hist_stmt = hist_stmt.where(Mantenimiento.fecha <= hasta)
        historial = db.session.execute(hist_stmt).scalars().unique().all()

        items.append({
            "equipo": equipo,
            "historial": historial,
            "proyeccion": calcular_vencimientos(equipo),
        })

    return {
        "cliente": cliente,
        "items": items,
        "fecha_generacion": date.today(),
        "equipo_id": equipo_id,
        "desde": desde,
        "hasta": hasta,
    }


def get_reporte_componentes_cambiados(desde, hasta, zona_id=None, cliente_id=None) -> dict:
    stmt = (
        select(Componente, func.count(DetalleMantenimiento.id).label("total"))
        .join(DetalleMantenimiento, DetalleMantenimiento.componente_id == Componente.id)
        .join(Mantenimiento, DetalleMantenimiento.mantenimiento_id == Mantenimiento.id)
        .where(
            Mantenimiento.fecha.between(desde, hasta),
            DetalleMantenimiento.accion == "reemplazo",
            Mantenimiento.completado == True,
            Mantenimiento.motivo_anulacion == None,
        )
    )

    if zona_id or cliente_id:
        stmt = stmt.join(EquipoInstalado, Mantenimiento.equipo_id == EquipoInstalado.id)
        if zona_id:
            stmt = stmt.where(EquipoInstalado.zona_id == zona_id)
        if cliente_id:
            stmt = stmt.where(EquipoInstalado.cliente_id == cliente_id)

    stmt = stmt.group_by(Componente.id).order_by(func.count(DetalleMantenimiento.id).desc())

    filas = db.session.execute(stmt).all()
    meses = max((hasta - desde).days / 30, 1)
    items = [
        {"componente": componente, "total": total, "promedio_mensual": total / meses}
        for componente, total in filas
    ]

    return {
        "items": items,
        "total_reemplazos": sum(i["total"] for i in items),
        "desde": desde,
        "hasta": hasta,
        "zona_id": zona_id,
        "cliente_id": cliente_id,
        "fecha_generacion": date.today(),
    }


# ── Render PDF del reporte de zona (reportlab) ────────────────────────────────
# Se migró de WeasyPrint a reportlab (#30): WeasyPrint era CPU-bound (98.5% del
# tiempo en su motor de layout CSS) y no alcanzaba el criterio JMeter <=5 s en PA
# Developer. reportlab (Platypus, layout imperativo sin motor CSS) rinde ~5x más
# rápido y libera los workers de PA. Ver docs/decisions.md D16. El PDF de cliente
# sigue en WeasyPrint. Import reportlab lazy (igual que WeasyPrint en AGENTS.md).

_AZUL = "#0d6efd"
_ROJO = "#dc3545"
_NARANJA = "#fd7e14"
_VERDE = "#198754"
_GRIS = "#6c757d"
_TINTE_VENCIDO = "#fbeeec"
_TINTE_PROXIMO = "#fbf1e2"
_TINTE_EN_PLAZO = "#eaf5ef"
_BORDE = "#e9ecef"

_ESTADO_POR_URGENCIA = {
    "vencido": ("Vencido", _ROJO, _TINTE_VENCIDO),
    "proximo": ("Próximo", _NARANJA, _TINTE_PROXIMO),
    "en_plazo": ("En plazo", _VERDE, _TINTE_EN_PLAZO),
}

_MESES = ["", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
          "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def _fecha_larga(d):
    return f"{d.day} de {_MESES[d.month]} de {d.year}"


def _esc(v):
    return escape(str(v)) if v is not None else ""


def _badge(texto, fondo):
    return f'<font backColor="{fondo}" color="white"> {_esc(texto)} </font>'


def build_reporte_zona_pdf(datos):
    """Renderiza el reporte de zona a PDF (bytes) con reportlab.

    `datos` es la salida de get_reporte_zona(): zona, items, resumen, fecha_ref,
    fecha_generacion. Replica el contenido del diseño bloque-por-equipo (#30):
    encabezado, 4 cajas de resumen, un bloque por equipo (cliente, tipo, serie,
    estado y sus componentes vencidos/próximos con fecha, días y fuente).
    """
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_RIGHT, TA_CENTER
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether,
    )
    from reportlab.pdfgen import canvas

    class NumberedCanvas(canvas.Canvas):
        """'Página X de Y': difiere el save para conocer el total de páginas."""

        def __init__(self, *args, **kwargs):
            canvas.Canvas.__init__(self, *args, **kwargs)
            self._saved_page_states = []

        def showPage(self):
            self._saved_page_states.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            num_pages = len(self._saved_page_states)
            for state in self._saved_page_states:
                self.__dict__.update(state)
                self.setFont("Helvetica", 8)
                self.setFillColor(colors.HexColor(_GRIS))
                self.drawCentredString(landscape(A4)[0] / 2.0, 1.0 * cm,
                                       f"Página {self._pageNumber} de {num_pages}")
                canvas.Canvas.showPage(self)
            canvas.Canvas.save(self)

    zona = datos["zona"]
    resumen = datos["resumen"]
    items = datos["items"]

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=landscape(A4),
        topMargin=1.8 * cm, bottomMargin=1.8 * cm,
        leftMargin=2 * cm, rightMargin=2 * cm,
        title=f"Reporte Zona {zona.nombre}",
    )
    ancho = doc.width

    st_brand = ParagraphStyle("brand", fontName="Helvetica-Bold", fontSize=16,
                              textColor=colors.HexColor(_AZUL), leading=18)
    st_sub = ParagraphStyle("sub", fontName="Helvetica", fontSize=8,
                            textColor=colors.HexColor(_GRIS), leading=10)
    st_meta = ParagraphStyle("meta", fontName="Helvetica", fontSize=8,
                             textColor=colors.HexColor(_GRIS), alignment=TA_RIGHT,
                             leading=11)
    st_num = ParagraphStyle("num", fontName="Helvetica-Bold", fontSize=18,
                            alignment=TA_CENTER, leading=20)
    st_lbl = ParagraphStyle("lbl", fontName="Helvetica", fontSize=7.5,
                            textColor=colors.HexColor(_GRIS), alignment=TA_CENTER,
                            leading=9)
    st_thead = ParagraphStyle("thead", fontName="Helvetica-Bold", fontSize=7.5,
                              textColor=colors.HexColor(_GRIS), leading=10,
                              spaceBefore=2, spaceAfter=2)
    st_head = ParagraphStyle("ehead", fontName="Helvetica", fontSize=9, leading=12)
    st_comp = ParagraphStyle("comp", fontName="Helvetica", fontSize=8.5, leading=11)
    st_comp_dias = ParagraphStyle("comp_dias", parent=st_comp, fontName="Helvetica",
                                  textColor=colors.HexColor(_GRIS))
    st_comp_estado = ParagraphStyle("comp_estado", parent=st_comp, fontName="Helvetica-Bold")
    st_footer = ParagraphStyle("footer", fontName="Helvetica", fontSize=7.5,
                               textColor=colors.HexColor(_GRIS), leading=10)
    st_vacio = ParagraphStyle("vacio", fontName="Helvetica", fontSize=9,
                              textColor=colors.HexColor(_GRIS))

    flow = []

    izq = [Paragraph("Watermax", st_brand),
           Paragraph("Sistema de gestión de mantenimiento preventivo", st_sub)]
    der = [Paragraph(f'<b><font size="11" color="#212529">Reporte por zona — '
                     f'{_esc(zona.nombre)}</font></b>', st_meta),
           Paragraph(f"Proyección al: {_fecha_larga(datos['fecha_ref'])}", st_meta),
           Paragraph(f"Generado: {datos['fecha_generacion'].strftime('%d/%m/%Y')}",
                     st_meta)]
    header = Table([[izq, der]], colWidths=[ancho * 0.55, ancho * 0.45])
    header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LINEBELOW", (0, 0), (-1, -1), 2, colors.HexColor(_AZUL)),
    ]))
    flow.append(header)
    flow.append(Spacer(1, 12))

    cajas = [
        (resumen["total"], "Total equipos", _AZUL),
        (resumen["vencidos"], "Con vencidos", _ROJO),
        (resumen["proximos"], "Próximos a vencer", _NARANJA),
        (resumen["en_plazo"], "En plazo", _VERDE),
    ]
    fila = [[Paragraph(f'<font color="{c}">{n}</font>', st_num),
             Paragraph(_esc(lbl).upper(), st_lbl)] for (n, lbl, c) in cajas]
    nb = len(cajas)
    gap = 0.18 * cm
    wbox = (ancho - gap * (nb - 1)) / nb
    resumen_tbl = Table([fila], colWidths=[wbox] * nb)
    estilo = [
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]
    for i, (_, _, c) in enumerate(cajas):
        estilo.append(("BOX", (i, 0), (i, 0), 1, colors.HexColor(c)))
    resumen_tbl.setStyle(TableStyle(estilo))
    flow.append(resumen_tbl)
    flow.append(Spacer(1, 14))

    if not items:
        flow.append(Paragraph("No hay equipos activos registrados en esta zona.",
                              st_vacio))
    else:
        thead = Table(
            [[Paragraph("Equipos por prioridad — cliente · equipo · serie · estado",
                        st_thead)]],
            colWidths=[ancho])
        thead.setStyle(TableStyle([
            ("LINEBELOW", (0, 0), (-1, -1), 2, colors.HexColor("#dee2e6")),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        flow.append(thead)

        for item in items:
            eq = item["equipo"]
            if item["n_vencidos"] > 0:
                estado = _badge("Vencido", _ROJO)
            elif item["n_proximos"] > 0:
                estado = _badge("Próximo", _NARANJA)
            else:
                estado = _badge("En plazo", _VERDE)

            dirpart = (f' <font color="{_GRIS}">· {_esc(eq.cliente.direccion)}</font>'
                       if eq.cliente.direccion else "")
            head = (
                f"<b>{_esc(eq.cliente.nombre)}</b>{dirpart}"
                f'  {_badge(eq.tipo_equipo.nombre, _GRIS)}'
                f'  <font face="Courier">{_esc(eq.numero_serie or "—")}</font>'
                f"  {estado}"
            )
            if item["n_vencidos"]:
                head += f'  {_badge(str(item["n_vencidos"]) + " vencidos", _ROJO)}'
            if item["n_proximos"]:
                head += f'  {_badge(str(item["n_proximos"]) + " próximos", _NARANJA)}'

            filas_tabla = [[Paragraph(head, st_head), "", ""]]
            fila_estilos = [
                ("SPAN", (0, 0), (-1, 0)),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f8f9fa")),
            ]
            for i, v in enumerate(item["vencimientos"], start=1):
                d = v["dias_restantes"]
                if d < 0:
                    plazo = f"hace {-d} d"
                elif d == 0:
                    plazo = "hoy"
                else:
                    plazo = f"en {d} d"
                nombre_estado, color_estado, tinte_fila = _ESTADO_POR_URGENCIA[v["urgencia"]]
                filas_tabla.append([
                    Paragraph(f'<b>{_esc(v["componente"].nombre)}</b>', st_comp),
                    Paragraph(f'vence {v["fecha_proyectada"].strftime("%d/%m/%Y")} — {plazo}',
                              st_comp_dias),
                    Paragraph(f'<font color="{color_estado}">{nombre_estado}</font>',
                              st_comp_estado),
                ])
                fila_estilos.append(
                    ("BACKGROUND", (0, i), (-1, i), colors.HexColor(tinte_fila))
                )

            bloque = Table(filas_tabla, colWidths=[ancho * 0.5, ancho * 0.35, ancho * 0.15])
            fila_estilos += [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LINEBELOW", (0, 0), (-1, -2), 0.5, colors.HexColor(_BORDE)),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor(_BORDE)),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
            bloque.setStyle(TableStyle(fila_estilos))
            flow.append(KeepTogether(bloque))
            flow.append(Spacer(1, 6))

    flow.append(Spacer(1, 16))
    pie = (f"Watermax · Reporte generado automáticamente el "
           f"{datos['fecha_generacion'].strftime('%d/%m/%Y')} · "
           f"Zona: {_esc(zona.nombre)}")
    if zona.descripcion:
        pie += f" — {_esc(zona.descripcion)}"
    pie_tbl = Table([[Paragraph(pie, st_footer)]], colWidths=[ancho])
    pie_tbl.setStyle(TableStyle([
        ("LINEABOVE", (0, 0), (-1, -1), 0.5, colors.HexColor("#dee2e6")),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
    ]))
    flow.append(pie_tbl)

    doc.build(flow, canvasmaker=NumberedCanvas)
    return buf.getvalue()
