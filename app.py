import streamlit as st
import pandas as pd
from datetime import datetime
from fpdf import FPDF
import os
import re
import textwrap

# =====================================================
# CONFIGURACION GENERAL
# =====================================================

st.set_page_config(
    page_title="Presupuestos Hormigon",
    page_icon="📄",
    layout="wide"
)

CARPETA_PDF = "presupuestos_pdf"
ARCHIVO_EXCEL = "historico_presupuestos.xlsx"

os.makedirs(CARPETA_PDF, exist_ok=True)

LOGOS_POSIBLES = ["logo.png", "logo.jpg", "logo.jpeg"]

LOGO_DERECHA_1 = "logo_derecha_1.png"
LOGO_DERECHA_2 = "logo_derecha_2.png"


# =====================================================
# FUNCIONES AUXILIARES
# =====================================================

def buscar_logo():
    for logo in LOGOS_POSIBLES:
        if os.path.exists(logo):
            return logo
    return None


def buscar_logo_derecha_1():
    if os.path.exists(LOGO_DERECHA_1):
        return LOGO_DERECHA_1
    return None


def buscar_logo_derecha_2():
    if os.path.exists(LOGO_DERECHA_2):
        return LOGO_DERECHA_2
    return None


def texto_seguro(texto):
    if texto is None:
        return ""

    texto = str(texto)

    cambios = {
        "€": "EUR",
        "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u",
        "Á": "A", "É": "E", "Í": "I", "Ó": "O", "Ú": "U",
        "ñ": "n", "Ñ": "N",
        "ü": "u", "Ü": "U",
        "º": "o", "ª": "a",
        "–": "-", "—": "-",
        "“": '"', "”": '"',
        "’": "'",
    }

    for original, reemplazo in cambios.items():
        texto = texto.replace(original, reemplazo)

    return texto


def limpiar_nombre_archivo(texto):
    texto = texto_seguro(texto).strip()
    texto = re.sub(r'[\\/*?:"<>|]', "", texto)
    texto = texto.replace(" ", "_")
    if texto == "":
        texto = "SIN_CLIENTE"
    return texto


def formato_numero(numero):
    try:
        numero = float(numero)
        return f"{numero:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "0,00"


def obtener_siguiente_numero():
    año = datetime.today().strftime("%y")

    if os.path.exists(ARCHIVO_EXCEL):
        try:
            df = pd.read_excel(ARCHIVO_EXCEL, sheet_name="Resumen")

            if not df.empty and "Nº Presupuesto" in df.columns:
                ultimo = str(df["Nº Presupuesto"].iloc[-1])
                match = re.search(r"PH(\d+)/", ultimo)

                if match:
                    numero = int(match.group(1)) + 1
                    return f"PH{numero:03d}/{año}"

        except Exception:
            pass

    return f"PH001/{año}"


# =====================================================
# TABLAS INICIALES
# =====================================================

TIPOS_HORMIGON = [
    "",
    "HORMIGON HL150-B-22",
    "HORMIGON HM20-B-22-X0",
    "HORMIGON HA25-B-22-XC1/XC2",
    "HORMIGON HA30-B-22-XC1/XC2",
]


def crear_tabla_hormigon():
    datos = []

    for i in range(1, 8):
        datos.append(
            {
                "Codigo": f"001.{i:03d}",
                "Concepto": "",
                "Ud.": "m3",
                "Cantidad": 0.00,
                "Precio/ud.": 0.00,
            }
        )

    return pd.DataFrame(datos)


def crear_tabla_otros_conceptos():
    datos = [
        ["002.001", "INCREMENTO ARIDO 14mm", "m3", 0.00, 4.00],
        ["002.002", "INCREMENTO CONSISTENCIA FLUIDA", "m3", 0.00, 4.00],
        ["002.003", "INCREMENTO CONSISTENCIA LIQUIDA", "m3", 0.00, 6.00],
        ["002.004", "INCREMENTO HIDROFUGO", "m3", 0.00, 5.00],
        ["002.005", "INCREMENTO CARGA INCOMPLETA HASTA 6m3", "ud", 0.00, 17.00],
        ["002.006", "INCREMENTO TIEMPO EXCESO DESCARGA", "h", 0.00, 60.00],
        ["002.007", "INCREMENTO FIBRA POLIPROPILENO 12 mm", "m3", 0.00, 5.00],
        ["002.008", "INCREMENTO RETARDANTE 12 Hrs", "m3", 0.00, 3.00],
        ["002.009", "INCREMENTO RETARDANTE 24 Hrs", "m3", 0.00, 6.00],
    ]

    return pd.DataFrame(
        datos,
        columns=["Codigo", "Concepto", "Ud.", "Cantidad", "Precio/ud."]
    )


def preparar_partidas(df, capitulo):
    df = df.copy()

    columnas = ["Codigo", "Concepto", "Ud.", "Cantidad", "Precio/ud."]
    for col in columnas:
        if col not in df.columns:
            df[col] = ""

    df["Cantidad"] = pd.to_numeric(df["Cantidad"], errors="coerce").fillna(0)
    df["Precio/ud."] = pd.to_numeric(df["Precio/ud."], errors="coerce").fillna(0)

    df["Importe"] = df["Cantidad"] * df["Precio/ud."]
    df["Capitulo"] = capitulo

    df = df[
        (df["Concepto"].astype(str).str.strip() != "") &
        (df["Cantidad"] > 0)
    ]

    return df[["Codigo", "Capitulo", "Concepto", "Ud.", "Cantidad", "Precio/ud.", "Importe"]]


def guardar_en_excel(resumen, partidas):
    resumen_df = pd.DataFrame([resumen])

    partidas_df = partidas.copy()
    partidas_df.insert(0, "Nº Presupuesto", resumen["Nº Presupuesto"])
    partidas_df.insert(1, "Fecha", resumen["Fecha"])
    partidas_df.insert(2, "Cliente", resumen["Cliente"])
    partidas_df.insert(3, "Obra", resumen["Obra"])

    if os.path.exists(ARCHIVO_EXCEL):
        try:
            resumen_existente = pd.read_excel(ARCHIVO_EXCEL, sheet_name="Resumen")
        except:
            resumen_existente = pd.DataFrame()

        try:
            partidas_existentes = pd.read_excel(ARCHIVO_EXCEL, sheet_name="Partidas")
        except:
            partidas_existentes = pd.DataFrame()

        resumen_final = pd.concat([resumen_existente, resumen_df], ignore_index=True)
        partidas_final = pd.concat([partidas_existentes, partidas_df], ignore_index=True)

    else:
        resumen_final = resumen_df
        partidas_final = partidas_df

    with pd.ExcelWriter(ARCHIVO_EXCEL, engine="openpyxl") as writer:
        resumen_final.to_excel(writer, sheet_name="Resumen", index=False)
        partidas_final.to_excel(writer, sheet_name="Partidas", index=False)


# =====================================================
# PDF
# =====================================================

class PDFPresupuesto(FPDF):

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "", 8)
        self.cell(0, 10, f"Pagina {self.page_no()}", align="C")


def comprobar_salto_pagina(pdf, altura_necesaria):
    if pdf.get_y() + altura_necesaria > 275:
        pdf.add_page()


def escribir_texto_largo(pdf, texto, ancho=185, alto=4):
    texto = texto_seguro(texto)

    if texto.strip() == "":
        pdf.ln(alto)
        return

    for parrafo in texto.split("\n"):
        pdf.set_x(10)

        if parrafo.strip() == "":
            pdf.ln(alto)
        else:
            lineas = textwrap.wrap(
                parrafo,
                width=110,
                break_long_words=True,
                break_on_hyphens=True
            )

            for linea in lineas:
                comprobar_salto_pagina(pdf, alto + 2)
                pdf.set_x(10)
                pdf.multi_cell(ancho, alto, linea)


def escribir_fila_tabla(pdf, codigo, concepto, ud, cantidad, precio, importe):
    codigo = texto_seguro(codigo)
    concepto = texto_seguro(concepto)
    ud = texto_seguro(ud)

    concepto_lineas = textwrap.wrap(
        concepto,
        width=48,
        break_long_words=True,
        break_on_hyphens=True
    )

    if len(concepto_lineas) == 0:
        concepto_lineas = [""]

    alto_linea = 5
    alto_fila = max(7, len(concepto_lineas) * alto_linea)

    comprobar_salto_pagina(pdf, alto_fila + 5)

    x = pdf.get_x()
    y = pdf.get_y()

    pdf.set_font("Arial", "", 8)

    pdf.rect(x, y, 22, alto_fila)
    pdf.rect(x + 22, y, 82, alto_fila)
    pdf.rect(x + 104, y, 14, alto_fila)
    pdf.rect(x + 118, y, 24, alto_fila)
    pdf.rect(x + 142, y, 24, alto_fila)
    pdf.rect(x + 166, y, 24, alto_fila)

    pdf.set_xy(x + 1, y + 1)
    pdf.cell(20, 5, codigo)

    pdf.set_xy(x + 23, y + 1)
    for linea in concepto_lineas:
        pdf.cell(80, alto_linea, linea, ln=True)
        pdf.set_x(x + 23)

    pdf.set_xy(x + 105, y + 1)
    pdf.cell(12, 5, ud, align="C")

    pdf.set_xy(x + 119, y + 1)
    pdf.cell(22, 5, formato_numero(cantidad), align="R")

    pdf.set_xy(x + 143, y + 1)
    pdf.cell(22, 5, formato_numero(precio), align="R")

    pdf.set_xy(x + 167, y + 1)
    pdf.cell(22, 5, formato_numero(importe), align="R")

    pdf.set_xy(x, y + alto_fila)


def insertar_cabecera_pdf(pdf, logo, datos=None, mostrar_cliente=True):
    """
    Logo principal superior izquierdo:
    8,5 cm x 3,5 cm = 85 mm x 35 mm

    Logos derechos:
    2 cm ancho x 3 cm alto = 20 mm x 30 mm
    """

    logo_dcha_1 = buscar_logo_derecha_1()
    logo_dcha_2 = buscar_logo_derecha_2()

    # Logo principal izquierda
    if logo:
        try:
            pdf.image(logo, x=10, y=8, w=85, h=35)
        except:
            pdf.set_xy(10, 10)
            pdf.set_font("Arial", "B", 14)
            pdf.cell(85, 8, "HITAMARIN IBERICA S.L.U.", ln=True)
    else:
        pdf.set_xy(10, 10)
        pdf.set_font("Arial", "B", 14)
        pdf.cell(85, 8, "HITAMARIN IBERICA S.L.U.", ln=True)

    # Logo derecho 1: 2 cm x 3 cm
    if logo_dcha_1:
        try:
            pdf.image(logo_dcha_1, x=150, y=10, w=20, h=30)
        except:
            pass

    # Logo derecho 2: 2 cm x 3 cm
    if logo_dcha_2:
        try:
            pdf.image(logo_dcha_2, x=175, y=10, w=20, h=30)
        except:
            pass

    # Datos del cliente bajados aproximadamente 6 cm desde el margen superior
    if datos and mostrar_cliente:
        pdf.set_xy(115, 60)
        pdf.set_font("Arial", "B", 9)
        pdf.cell(80, 5, texto_seguro(datos["Cliente"]), ln=True)

        pdf.set_x(115)
        pdf.set_font("Arial", "", 8)
        pdf.cell(80, 5, texto_seguro(datos["Direccion cliente"]), ln=True)

        pdf.set_x(115)
        pdf.cell(80, 5, texto_seguro(datos["Poblacion cliente"]), ln=True)

        pdf.set_x(115)
        pdf.cell(80, 5, f"Telf: {texto_seguro(datos['Telefono cliente'])}", ln=True)

        pdf.set_x(115)
        pdf.cell(80, 5, f"C.I.F./N.I.F.: {texto_seguro(datos['CIF/NIF cliente'])}", ln=True)


def generar_pdf(datos, partidas):
    cliente_archivo = limpiar_nombre_archivo(datos["Cliente"])
    numero_archivo = limpiar_nombre_archivo(datos["Nº Presupuesto"].replace("/", "-"))

    nombre_pdf = f"{numero_archivo}_{cliente_archivo}.pdf"
    ruta_pdf = os.path.join(CARPETA_PDF, nombre_pdf)

    logo = buscar_logo()

    pdf = PDFPresupuesto()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # =====================================================
    # PRIMERA PAGINA - CABECERA
    # =====================================================

    insertar_cabecera_pdf(pdf, logo, datos, mostrar_cliente=True)

    # Titulo PRESUPUESTO con fondo azul solo sobre el texto
    pdf.set_y(50)
    pdf.set_x(10)

    pdf.set_fill_color(28, 42, 90)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", "B", 16)

    texto_titulo = "P R E S U P U E S T O"
    ancho_franja_presupuesto = pdf.get_string_width(texto_titulo) + 6

    pdf.cell(
        ancho_franja_presupuesto,
        9,
        texto_titulo,
        ln=True,
        align="L",
        fill=True
    )

    pdf.set_text_color(0, 0, 0)

    # Espacio para que no se pise con los datos del cliente
    pdf.ln(30)
    pdf.set_x(10)

    pdf.set_font("Arial", "B", 10)
    linea_presupuesto = f"{datos['Nº Presupuesto']} - {datos['Obra']} - {datos['Localidad obra']}"
    pdf.cell(0, 7, texto_seguro(linea_presupuesto), ln=True)

    pdf.set_x(10)
    pdf.set_font("Arial", "", 9)
    pdf.cell(0, 6, f"Fecha: {texto_seguro(datos['Fecha'])}", ln=True)

    pdf.ln(3)
    pdf.set_x(10)

    # =====================================================
    # TABLA DE PARTIDAS
    # =====================================================

    pdf.set_font("Arial", "B", 8)
    pdf.set_fill_color(230, 230, 230)

    pdf.cell(22, 7, "Codigo", border=1, align="C", fill=True)
    pdf.cell(82, 7, "Concepto", border=1, align="C", fill=True)
    pdf.cell(14, 7, "Ud.", border=1, align="C", fill=True)
    pdf.cell(24, 7, "Cantidad", border=1, align="C", fill=True)
    pdf.cell(24, 7, "Precio/ud.", border=1, align="C", fill=True)
    pdf.cell(24, 7, "Importe", border=1, align="C", fill=True)
    pdf.ln()

    # =====================================================
    # CAPITULOS FIJOS
    # =====================================================

    total_base = 0

    capitulos_fijos = [
        ("1", "SUMINISTRO DE HORMIGON"),
        ("2", "OTROS CONCEPTOS DE SUMINISTRO"),
    ]

    for numero_capitulo, capitulo in capitulos_fijos:

        grupo = partidas[partidas["Capitulo"] == capitulo]

        comprobar_salto_pagina(pdf, 12)
        pdf.set_x(10)

        pdf.set_font("Arial", "B", 9)
        pdf.cell(0, 7, f"{numero_capitulo} Capitulo: {capitulo}", ln=True)

        total_capitulo = 0

        for _, fila in grupo.iterrows():
            importe = float(fila["Importe"])
            total_capitulo += importe
            total_base += importe

            pdf.set_x(10)

            escribir_fila_tabla(
                pdf,
                fila["Codigo"],
                fila["Concepto"],
                fila["Ud."],
                fila["Cantidad"],
                fila["Precio/ud."],
                importe
            )

        comprobar_salto_pagina(pdf, 10)
        pdf.set_x(10)

        pdf.set_font("Arial", "B", 9)
        pdf.cell(166, 7, "Importe del capitulo:", align="R")
        pdf.cell(24, 7, formato_numero(total_capitulo), align="R")
        pdf.ln(9)

    # =====================================================
    # TOTALES
    # =====================================================

    descuento_porcentaje = float(datos["Dto %"])
    iva_porcentaje = float(datos["IVA %"])

    descuento_importe = total_base * descuento_porcentaje / 100
    base_imponible = total_base - descuento_importe
    iva_importe = base_imponible * iva_porcentaje / 100
    total_presupuesto = base_imponible + iva_importe

    comprobar_salto_pagina(pdf, 40)

    pdf.ln(3)
    pdf.set_x(10)

    pdf.set_font("Arial", "", 9)
    pdf.cell(120, 7, "", border=0)
    pdf.cell(35, 7, "Base imponible", border=1, align="C")
    pdf.cell(20, 7, "IVA %", border=1, align="C")
    pdf.cell(25, 7, "Importe IVA", border=1, align="C")
    pdf.ln()

    pdf.set_x(10)
    pdf.cell(120, 7, "", border=0)
    pdf.cell(35, 7, formato_numero(base_imponible), border=1, align="R")
    pdf.cell(20, 7, formato_numero(iva_porcentaje), border=1, align="R")
    pdf.cell(25, 7, formato_numero(iva_importe), border=1, align="R")
    pdf.ln(10)

    if descuento_porcentaje > 0:
        pdf.set_x(10)
        pdf.cell(120, 7, "", border=0)
        pdf.cell(35, 7, "Descuento", border=1, align="C")
        pdf.cell(20, 7, formato_numero(descuento_porcentaje) + " %", border=1, align="R")
        pdf.cell(25, 7, formato_numero(descuento_importe), border=1, align="R")
        pdf.ln(10)

    pdf.set_x(10)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(150, 10, "T O T A L   P R E S U P U E S T O", align="R")
    pdf.cell(40, 10, formato_numero(total_presupuesto), border=1, align="R")
    pdf.ln(10)

    # =====================================================
    # SEGUNDA PAGINA - CONDICIONES
    # =====================================================

    pdf.add_page()

    insertar_cabecera_pdf(pdf, logo, datos, mostrar_cliente=False)

    pdf.set_y(50)
    pdf.set_x(10)

    # Nº de presupuesto y obra encima de Exclusiones
    pdf.set_font("Arial", "B", 9)
    linea_segunda_pagina = f"{datos['Nº Presupuesto']} - {datos['Obra']}"
    pdf.cell(0, 6, texto_seguro(linea_segunda_pagina), ln=True)

    pdf.ln(2)
    pdf.set_x(10)

    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 6, "Exclusiones:", ln=True)

    pdf.set_x(10)
    pdf.set_font("Arial", "", 8)
    escribir_texto_largo(pdf, datos["Exclusiones"], ancho=185, alto=4)

    pdf.ln(4)
    pdf.set_x(10)

    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 6, "Condiciones y reservas:", ln=True)

    pdf.set_x(10)
    pdf.set_font("Arial", "", 8)
    escribir_texto_largo(pdf, datos["Condiciones"], ancho=185, alto=4)

    pdf.ln(4)
    pdf.set_x(10)

    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 6, "Proteccion de datos:", ln=True)

    pdf.set_x(10)
    pdf.set_font("Arial", "", 8)
    escribir_texto_largo(pdf, datos["Proteccion datos"], ancho=185, alto=4)

    if pdf.get_y() > 235:
        pdf.add_page()
        insertar_cabecera_pdf(pdf, logo, datos, mostrar_cliente=False)
        pdf.set_y(55)
        pdf.set_x(10)

    pdf.ln(10)
    pdf.set_x(10)

    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 8, "ACEPTO/CONFORME", ln=True)

    pdf.ln(18)
    pdf.set_x(10)

    pdf.set_font("Arial", "", 10)
    pdf.cell(80, 8, "(FIRMA Y SELLO)", border="T", align="C")

    pdf.output(ruta_pdf)

    datos["Base imponible"] = base_imponible
    datos["IVA importe"] = iva_importe
    datos["Total"] = total_presupuesto
    datos["Dto importe"] = descuento_importe

    return ruta_pdf, datos


# =====================================================
# APP
# =====================================================

logo = buscar_logo()

if logo:
    st.image(logo, width=650)

st.title("Generador de presupuestos de hormigon")

numero_presupuesto = obtener_siguiente_numero()
fecha_actual = datetime.today().strftime("%d/%m/%Y")

st.subheader("Datos del presupuesto")

col1, col2, col3 = st.columns(3)

with col1:
    numero = st.text_input("Nº presupuesto", value=numero_presupuesto)

with col2:
    fecha = st.text_input("Fecha", value=fecha_actual)

with col3:
    iva_porcentaje = st.selectbox("IVA", options=[21, 10, 4, 0], index=0)

obra = st.text_input("Nombre de la obra", value="")
localidad_obra = st.text_input("Localidad / provincia de la obra", value="GRANADA")


st.subheader("Datos del cliente")

col1, col2 = st.columns(2)

with col1:
    cliente = st.text_input("Cliente", value="")
    cif_cliente = st.text_input("CIF / NIF cliente", value="")
    telefono_cliente = st.text_input("Telefono", value="")

with col2:
    direccion_cliente = st.text_area("Direccion cliente", value="")
    poblacion_cliente = st.text_input("Poblacion / CP", value="")


st.subheader("1. Capitulo: SUMINISTRO DE HORMIGON")

st.write("Selecciona el tipo de hormigon. La cantidad y el precio los puedes modificar manualmente.")

if "tabla_hormigon" not in st.session_state:
    st.session_state["tabla_hormigon"] = crear_tabla_hormigon()

tabla_hormigon_editada = st.data_editor(
    st.session_state["tabla_hormigon"],
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "Codigo": st.column_config.TextColumn("Codigo"),
        "Concepto": st.column_config.SelectboxColumn(
            "Tipo de hormigon",
            options=TIPOS_HORMIGON,
            required=False
        ),
        "Ud.": st.column_config.TextColumn("Ud."),
        "Cantidad": st.column_config.NumberColumn(
            "Cantidad",
            min_value=0.0,
            step=1.0,
            format="%.2f"
        ),
        "Precio/ud.": st.column_config.NumberColumn(
            "Precio/ud.",
            min_value=0.0,
            step=1.0,
            format="%.2f"
        ),
    }
)


st.subheader("2. Capitulo: OTROS CONCEPTOS DE SUMINISTRO")

st.write("Estos conceptos aparecen siempre por defecto. Para incluir uno en el PDF, pon cantidad mayor que 0.")

if "tabla_otros" not in st.session_state:
    st.session_state["tabla_otros"] = crear_tabla_otros_conceptos()

tabla_otros_editada = st.data_editor(
    st.session_state["tabla_otros"],
    num_rows="fixed",
    use_container_width=True,
    disabled=["Codigo", "Concepto"],
    column_config={
        "Codigo": st.column_config.TextColumn("Codigo"),
        "Concepto": st.column_config.TextColumn("Concepto"),
        "Ud.": st.column_config.TextColumn("Ud."),
        "Cantidad": st.column_config.NumberColumn(
            "Cantidad",
            min_value=0.0,
            step=1.0,
            format="%.2f"
        ),
        "Precio/ud.": st.column_config.NumberColumn(
            "Precio/ud.",
            min_value=0.0,
            step=1.0,
            format="%.2f"
        ),
    }
)


partidas_hormigon = preparar_partidas(tabla_hormigon_editada, "SUMINISTRO DE HORMIGON")
partidas_otros = preparar_partidas(tabla_otros_editada, "OTROS CONCEPTOS DE SUMINISTRO")

partidas = pd.concat([partidas_hormigon, partidas_otros], ignore_index=True)

st.subheader("Vista previa de importes")

if not partidas.empty:
    vista = partidas.copy()
    vista["Importe"] = vista["Importe"].round(2)

    st.dataframe(vista, use_container_width=True)

    base_previa = float(vista["Importe"].sum())
    iva_previo = base_previa * iva_porcentaje / 100
    total_previo = base_previa + iva_previo

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Base imponible", f"{formato_numero(base_previa)} €")

    with col2:
        st.metric("IVA", f"{formato_numero(iva_previo)} €")

    with col3:
        st.metric("Total", f"{formato_numero(total_previo)} €")

else:
    st.warning("Todavia no hay partidas validas.")


st.subheader("Descuento y condiciones")

col1, col2 = st.columns(2)

with col1:
    descuento_porcentaje = st.number_input(
        "Descuento %",
        min_value=0.0,
        max_value=100.0,
        value=0.0,
        step=1.0,
        format="%.2f"
    )

with col2:
    forma_pago = st.text_input("Forma de pago", value="Confirming hasta 120 dias f. factura")

validez = st.text_input("Validez de la oferta", value="15 dias naturales")

exclusiones = st.text_area(
    "Exclusiones",
    value=(
        "Replanteos, seguimientos topograficos, permisos, tasas y/o licencias municipales, "
        "estudios tecnicos, seguros especificos, avales o fianzas, u otro tipo de gravamenes "
        "solicitados por los titulares de las vias o solares colindantes a la obra o titulares "
        "de los servicios y/o suministros afectados por la obra."
    ),
    height=100
)

condiciones = st.text_area(
    "Condiciones y reservas",
    value=(
        "El presente presupuesto, en caso de ser aceptado, debe ser devuelto por email "
        "debidamente firmado y sellado, sirviendo el mismo como pedido aceptado o posterior contrato.\n\n"
        f"Validez de la oferta: {validez}.\n"
        f"Forma de pago: {forma_pago}.\n"
        "Precios supeditados a revision por subida de precios de materias primas.\n\n"
        "El cliente se compromete a comunicar a la empresa HITAMARIN IBERICA SLU la ubicacion de las acometidas "
        "y/o servicios afectados en el terreno, asi como cualquier particularidad no detallada en la documentacion aportada.\n\n"
        "El inicio de los trabajos objeto del presente presupuesto debera ser comunicado por el cliente con el tiempo necesario "
        "para garantizar la correcta organizacion y ejecucion de los mismos."
    ),
    height=180
)

proteccion_datos = st.text_area(
    "Proteccion de datos",
    value=(
        "HITAMARIN IBERICA SLU es responsable del tratamiento de los datos facilitados, cuya finalidad es prestar "
        "el servicio contratado y realizar la facturacion del mismo. Los datos se conservaran mientras se mantenga "
        "la relacion comercial o durante los anos necesarios para cumplir con las obligaciones legales. "
        "Puede ejercer sus derechos de acceso, rectificacion, supresion, limitacion y oposicion conforme a la normativa vigente."
    ),
    height=120
)

st.divider()

boton_generar = st.button("Generar presupuesto PDF y guardar historico", type="primary")


if boton_generar:

    if cliente.strip() == "":
        st.error("Debes indicar el nombre del cliente.")

    elif obra.strip() == "":
        st.error("Debes indicar el nombre de la obra.")

    elif partidas.empty:
        st.error("Debes introducir al menos una partida valida.")

    else:
        resumen = {
            "Nº Presupuesto": numero,
            "Fecha": fecha,
            "Cliente": cliente,
            "CIF/NIF cliente": cif_cliente,
            "Direccion cliente": direccion_cliente,
            "Poblacion cliente": poblacion_cliente,
            "Telefono cliente": telefono_cliente,
            "Obra": obra,
            "Localidad obra": localidad_obra,
            "IVA %": iva_porcentaje,
            "Dto %": descuento_porcentaje,
            "Forma de pago": forma_pago,
            "Validez": validez,
            "Exclusiones": exclusiones,
            "Condiciones": condiciones,
            "Proteccion datos": proteccion_datos,
        }

        try:
            ruta_pdf, resumen_actualizado = generar_pdf(resumen, partidas)
            guardar_en_excel(resumen_actualizado, partidas)

            st.success("Presupuesto generado correctamente.")

            st.write(f"**Base imponible:** {formato_numero(resumen_actualizado['Base imponible'])} €")
            st.write(f"**IVA:** {formato_numero(resumen_actualizado['IVA importe'])} €")
            st.write(f"**Total:** {formato_numero(resumen_actualizado['Total'])} €")

            with open(ruta_pdf, "rb") as archivo:
                st.download_button(
                    label="Descargar PDF",
                    data=archivo,
                    file_name=os.path.basename(ruta_pdf),
                    mime="application/pdf"
                )

            with open(ARCHIVO_EXCEL, "rb") as archivo_excel:
                st.download_button(
                    label="Descargar historico Excel",
                    data=archivo_excel,
                    file_name=ARCHIVO_EXCEL,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

        except Exception as e:
            st.error("Ha ocurrido un error al generar el presupuesto.")
            st.exception(e)