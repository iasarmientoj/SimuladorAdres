import spacy
from spacy.matcher import Matcher
import os
import pdfplumber
import easyocr
import numpy as np
import difflib

# Cargar modelo de spaCy
try:
    nlp = spacy.load("es_core_news_sm")
except:
    print("Descargando modelo spaCy...")
    os.system("python -m spacy download es_core_news_sm")
    nlp = spacy.load("es_core_news_sm")

# ---------------------------------------------------------
# 1. FUNCIONES DE VALIDACIÓN Y CORRECCIÓN (ESTRICTAS)
# ---------------------------------------------------------

def validar_y_corregir_placa(palabra_raw):
    """
    Valida y corrige una posible placa.
    Incluye filtros anti-falsos positivos (ej: VATIOS -> VAT105).
    """
    # -----------------------------------------------------------
    # 1. FILTRO DE CARACTERES INVALIDANTES (Contexto inmediato)
    # -----------------------------------------------------------
    # Si la palabra original trae un slash (/), es una unidad de medida o etiqueta compuesta.
    # Ej: "CILINDRAJE/VATIOS" o "/VATIOS"
    if "/" in palabra_raw:
        return None

    # -----------------------------------------------------------
    # 2. LIMPIEZA
    # -----------------------------------------------------------
    # Quitamos puntuación externa, pero NO interna todavía.
    limpio = palabra_raw.strip(".,;:()[]-")
    limpio = limpio.upper()

    # -----------------------------------------------------------
    # 3. LISTA NEGRA (STOPWORDS DE SOAT)
    # -----------------------------------------------------------
    # Palabras comunes en el formato que al convertirlas parecen placas
    # VATIOS -> VAT105 (Falso positivo común)
    # MOTOS  -> MOT05
    # DATOS  -> DAT05
    PALABRAS_PROHIBIDAS = {
        "VATIOS", "CILINDRAJE", "MODELO", "CLASE", "DATOS", 
        "MOTOR", "SERIE", "CHASIS", "POLIZA", "TOTAL", "VALOR", 
        "FECHA", "DESDE", "HASTA", "MOTOS", "AUTO", "SITIO"
    }
    
    # Verificamos si la palabra (antes de volverla números) es una palabra prohibida
    # Usamos in para detectar si dice "VATIOS" o "DE/VATIOS"
    for prohibida in PALABRAS_PROHIBIDAS:
        if prohibida in limpio:
            return None

    # -----------------------------------------------------------
    # 4. VALIDACIÓN DE LONGITUD
    # -----------------------------------------------------------
    # Placa normal: 6 chars. Placa con guion: 7 chars.
    if len(limpio) < 6 or len(limpio) > 7:
        return None

    # Normalizamos quitando guion
    limpio = limpio.replace("-", "")

    # -----------------------------------------------------------
    # 5. CORRECCIÓN HEURÍSTICA (LLLDDD)
    # -----------------------------------------------------------
    parte_letras = limpio[:3]
    parte_numeros = limpio[3:]

    # Letras: 0->O, 1->I, 5->S
    parte_letras = parte_letras.translate(str.maketrans("015", "OIS"))
    
    # Números: O->0, I->1, S->5, B->8, Z->2
    parte_numeros = parte_numeros.translate(str.maketrans("OISBZ", "01582"))

    # -----------------------------------------------------------
    # 6. VALIDACIÓN FINAL DE ESTRUCTURA
    # -----------------------------------------------------------
    # Debe ser estrictamente 3 LETRAS y 3 DIGITOS
    if parte_letras.isalpha() and parte_numeros.isdigit():
        return parte_letras + parte_numeros
    
    return None

def intentar_reparar_monto(token_texto):
    """Convierte texto sucio en valor monetario."""
    limpio = token_texto.replace("$", "").replace(".", "").replace(",", "").replace(" ", "").upper()
    limpio = limpio.translate(str.maketrans("OISB", "0158")) # Correcciones visuales
    
    if limpio.isdigit():
        valor = int(limpio)
        # Filtro de lógica de negocio (Valor razonable SOAT)
        if 100000 < valor < 5000000: 
            return valor
    return None

# ---------------------------------------------------------
# 2. LÓGICA DE EXTRACCIÓN INTELIGENTE
# ---------------------------------------------------------

def extraer_con_inteligencia_hibrida(texto_completo):
    """
    Fase 1: Búsqueda Contextual (Cerca de palabras clave).
    Fase 2: Búsqueda por Fuerza Bruta en Cabecera (Primeras 30 palabras).
    """
    doc = nlp(texto_completo)
    matcher = Matcher(nlp.vocab)
    
    resultados = {"placa": None, "monto": None}

    # --- FASE 1: SPACY CONTEXTUAL ---
    
    # Patrones Ancla
    patron_placa = [[{"LOWER": "placa"}], [{"LOWER": "vehiculo"}], [{"LOWER": "modelo"}]]
    patron_monto = [[{"LOWER": "total"}, {"LOWER": "pagar"}], [{"LOWER": "legales"}]]

    matcher.add("ANCLA_PLACA", patron_placa)
    matcher.add("ANCLA_MONTO", patron_monto)

    matches = matcher(doc)

    for match_id, start, end in matches:
        string_id = nlp.vocab.strings[match_id]
        
        # Miramos los 8 tokens siguientes
        ventana = doc[end : end + 15] 
        
        if string_id == "ANCLA_PLACA" and not resultados["placa"]:
            for token in ventana:
                # Usamos la validación estricta
                candidato = validar_y_corregir_placa(token.text)
                if candidato:
                    resultados["placa"] = candidato
                    break
                    
        elif string_id == "ANCLA_MONTO" and not resultados["monto"]:
            for token in ventana:
                candidato = intentar_reparar_monto(token.text)
                if candidato:
                    resultados["monto"] = candidato
                    break

    # --- FASE 2: FALLBACK (BÚSQUEDA EN CABECERA) ---
    # Si spaCy falló al encontrar la placa por contexto, buscamos en las primeras 70 palabras.
    
    if not resultados["placa"]:
        print("   ⚠️ Placa no encontrada por contexto. Buscando en las primeras 70 palabras...")
        
        # Usamos split() nativo para respetar "espacio antes y después".
        # Esto crea una lista de palabras aisladas.
        palabras_cabecera = texto_completo.split()[:70]
        
        for palabra in palabras_cabecera:
            # Enviamos la palabra tal cual viene (con posibles signos de puntuación pegados)
            # La función validar_y_corregir_placa se encarga de limpiar bordes
            candidato = validar_y_corregir_placa(palabra)
            
            if candidato:
                print(f"   ✅ Placa encontrada en cabecera: {candidato}")
                resultados["placa"] = candidato
                break

    return resultados

# ---------------------------------------------------------
# 3. MOTORES DE LECTURA (PDF/IMG)
# ---------------------------------------------------------

TEXTO_REF = """
NIT. 860.009.578-6
FECHA DE EXPEDICIÓN VIGENCIA
2 A 0 ÑO 21- M 0 E 3 S -0 D 9 ÍA D L H A E O S S R D 0 A 0 E S 20 AÑ 2 O 1-0 M 3 ES -1 D 4 ÍA H L H A A O S S R T 2 A A 3 S : 59 2 A 0 ÑO 22-0 ME 3 S -1 D 3 ÍA
DEL DEL
No. DE PÓLIZA. PLACA No. CLASE VEHÍCULO SERVICIO CILINDRAJE/VATIOS MODELO
13706700001810 ASA534 CARGA O MIXTO PUBLICO 14011 1998
PASAJEROS MARCA KENWORTH CARROCERÍA
2 LÍNEA T800 SRS
VEHICULO
No. MOTOR No. CHASIS ó No. SERIE No. VIN CAPACIDAD TON.
11866782 R772485 35.00
APELLIDOS Y NOMBRES DEL TOMADOR TELÉFONO DEL TOMADOR TIPO DE DOCUMENTO No. DE DOCUMENTO CIUDAD RESIDENCIA TOMADOR
DEL TOMADOR DEL TOMADOR
GUEVARA TELLEZ, JENNY MARCELA 8053739 CC 1026261589 BOGOTA D.C
CÓDIGO DE ASEGURADORA CÓD. SUCURSAL EXPEDIDORA CLAVE PRODUCTOR No. FORMULARIO CIUDAD EXPEDICIÓN
AT1329 10 154005918 0 BOGOTA D.C
TARIFA PRIMA SOAT CONTRIBUCIÓN FOSYGA TASA RUNT AMPAROS POR VICTIMA HASTA
A. GASTOS MÉDICOS QUIRURGICOS, 800
330 $ 792800 $ 396400 $ 1800 FARMACÉUTICOS Y HOSPITALARIOS SALARIOS
B. INCAPACIDAD PERMANENTE 180 MÍNIMOS
TOTAL A PAGAR
LEGALES
$ 1191000 C. MUERTE Y GASTOS FUNERARIOS 750
DIARIOS
D GASTOS DE TRANSPORTE 10 VIGENTES
Y MOVILIZACIÓN DE VICTIMAS
FIRMA AUTORIZADA
Modificación unilateral de la vigencia por duplicidad de amparos: Con el fin de evitar duplicidad de amparos, en aquellos
eventos en que la aseguradora llegara a evidenciar que existe otra póliza vigente, ésta procederá a modificar la vigencia de
la (segunda) póliza expedida (expedida con posterioridad), iniciando la vigencia de la misma a partir del vencimiento de la
póliza que ya se encuentra registrada en el RUNT.
Señor usuario tenga en cuenta las siguientes recomendaciones: Protección de datos personales:
•Recuerde portar siempre su SOAT, las autoridades de tránsito se lo pueden solicitar en Con la inequívoca conducta de aceptar y no devolver la presente y en cumplimiento de la
cualquier momento. normatividad vigente de protección de datos personales, manifiesto que he autorizado a
•Recuerde validar que su póliza está registrada en el RUNT. Seguros del Estado S.A. y Seguros de Vida del Estado S.A., para que mis datos sean
•Esté atento al momento en que deba renovar su póliza. No tener SOAT vigente acarrea tratados con fines de la gestión y ejecución integral del contrato de seguros, los cuales
multas económicas, la detención del vehículo y en caso de accidente de tránsito el cobro por serán incluidos en una Base de Datos cuyo responsable son LAS ASEGURADORAS,
todos los costos de la atención de las víctimas del accidente. quienes podrán hacer transferencia internacional cuando sea necesario para la prestación
•Adquiera su SOAT en lugares autorizados. del servicio. Usted podrá manifestar la negativa al tratamiento de sus datos, así como a
conocer, actualizar y rectificar la información de conformidad con la política de tratamiento
En caso de accidente de tránsito: de datos personales publicada en la pagina www.segurosdelestado.com.
•Si alguien resulta herido, debe ser atendido por el prestador de servicios de salud más
cercano al lugar del accidente siempre que tenga la capacidad para brindar la atención
requerida por las víctimas.
•Ningún prestador de servicios de salud del país puede negarse a atender víctimas de
accidentes de tránsito (artículo 195 Decreto Ley 663 de 1993). En caso contrario, denuncie
ante la Superintendencia Nacional de Salud.
•Para los gastos médicos, el cobro ante la aseguradora o el Fosyga lo debe realizar la
institución prestadora de servicios de salud.
•Para presentar la reclamación ante la compañía aseguradora no se requiere acudir a
terceros.
"""

def evaluar_similitud(texto_base, texto_nuevo):
    if not texto_nuevo: return 0.0
    s1 = " ".join(texto_base.split()).lower()
    s2 = " ".join(texto_nuevo.split()).lower()
    return difflib.SequenceMatcher(None, s1, s2).ratio() * 100

def obtener_texto_con_ocr(ruta, modo_pdf=False):
    """Usa EasyOCR"""
    print("   ...Ejecutando EasyOCR...")
    try:
        reader = easyocr.Reader(['es'], gpu=True)
    except:
        reader = easyocr.Reader(['es'], gpu=False)
    
    texto_out = ""
    if modo_pdf:
        with pdfplumber.open(ruta) as pdf:
            # Solo primera página para SOAT
            im = pdf.pages[0].to_image(resolution=300)
            arr = np.array(im.original)
            res = reader.readtext(arr, detail=0)
            texto_out = " ".join(res)
    else:
        res = reader.readtext(ruta, detail=0)
        texto_out = " ".join(res)
        
    return texto_out

# ---------------------------------------------------------
# 4. FUNCIÓN PRINCIPAL
# ---------------------------------------------------------

# ... (Todo tu código de imports y funciones auxiliares VALIDAR/CORREGIR queda IGUAL) ...

def extraer_datos_soat(ruta_archivo):
    # Validar existencia
    if not os.path.exists(ruta_archivo):
        return {'exito': False, 'placa': None, 'monto': None, 'mensaje': "Archivo no encontrado"}

    try:
        ext = os.path.splitext(ruta_archivo)[1].lower()
        texto_final = ""
        origen = ""

        # A. Extracción del Texto Crudo
        if ext == '.pdf':
            with pdfplumber.open(ruta_archivo) as pdf:
                texto_nativo = pdf.pages[0].extract_text() if pdf.pages else ""
            
            similitud = evaluar_similitud(TEXTO_REF, texto_nativo)
            if similitud > 70.0:
                texto_final = texto_nativo
                origen = "Digital"
            else:
                # OJO: OCR es lento, esto puede tardar unos segundos
                texto_final = obtener_texto_con_ocr(ruta_archivo, modo_pdf=True)
                origen = "OCR Scan"
                
        elif ext in {'.jpg', '.jpeg', '.png'}:
            texto_final = obtener_texto_con_ocr(ruta_archivo, modo_pdf=False)
            origen = "OCR Imagen"
        else:
            return {'exito': False, 'mensaje': "Formato no soportado (Use PDF, JPG, PNG)"}

        # B. Procesamiento
        datos = extraer_con_inteligencia_hibrida(texto_final)
        
        placa = datos.get('placa')
        monto = datos.get('monto')

        # C. Validación Crítica (AQUI DECIDIMOS EL EXITO)
        if not placa:
            # Si no hay placa, fallamos. (El monto es secundario, pero la placa es vital)
            return {
                'exito': False, 
                'mensaje': "No pudimos detectar la PLACA. Intente con una foto más clara o un PDF digital."
            }

        # D. Retorno Exitoso
        return {
            'exito': True,
            'placa': placa,
            'monto': monto if monto else 0, # Si no hay monto, ponemos 0
            'origen': origen,
            'mensaje': "Lectura exitosa"
        }

    except Exception as e:
        return {'exito': False, 'mensaje': f"Error técnico analizando el archivo: {str(e)}"}