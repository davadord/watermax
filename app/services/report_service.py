from datetime import date
from io import BytesIO
from xml.sax.saxutils import escape
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from app import db
from app.models.client import Zona, Cliente
from app.models.equipment import EquipoInstalado, TipoEquipo, TipoEquipoComponente
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


def get_reporte_cliente(cliente_id: int) -> dict:
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
_TINTE_VENCIDO = "#fff5f5"
_TINTE_PROXIMO = "#fff8f0"
_BORDE = "#e9ecef"

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
    st_comp = ParagraphStyle("comp", fontName="Helvetica", fontSize=8.5,
                            leading=11, leftIndent=14)
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
                tinte, estado = _TINTE_VENCIDO, _badge("Vencido", _ROJO)
            elif item["n_proximos"] > 0:
                tinte, estado = _TINTE_PROXIMO, _badge("Próximo", _NARANJA)
            else:
                tinte, estado = "#ffffff", _badge("En plazo", _VERDE)

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

            celda = [Paragraph(head, st_head)]
            mostrar_en_plazo = datos.get("estado") is not None
            filas = [
                v for v in item["vencimientos"]
                if mostrar_en_plazo or v["urgencia"] != "en_plazo"
            ]
            for v in filas:
                d = v["dias_restantes"]
                if d < 0:
                    plazo = f"hace {-d} d"
                elif d == 0:
                    plazo = "hoy"
                else:
                    plazo = f"en {d} d"
                celda.append(Paragraph(
                    f'<b>{_esc(v["componente"].nombre)}</b> — vence '
                    f'{v["fecha_proyectada"].strftime("%d/%m/%Y")} — {plazo} '
                    f'<font color="{_GRIS}">({_esc(v["fuente"])})</font>',
                    st_comp))

            bloque = Table([[celda]], colWidths=[ancho])
            bloque.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(tinte)),
                ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor(_BORDE)),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]))
            flow.append(KeepTogether(bloque))

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
