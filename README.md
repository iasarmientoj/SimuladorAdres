# Sistema de Auditoría de SOAT con IA 🚗🔍

Plataforma web desarrollada en Django para la validación automática de Seguros Obligatorios (SOAT) utilizando OCR híbrido y validación gubernamental.

🔗 **Demo en vivo:** [https://i95sarmiento.pythonanywhere.com/auditoria/](https://i95sarmiento.pythonanywhere.com/auditoria/)

## 🚀 Funcionalidades Principales

* **Lectura Inteligente:** Extracción de datos (Placa, Monto) desde PDFs digitales e Imágenes usando `pdfplumber` y `EasyOCR` optimizado.
* **Validación de Fraude:** Cruce de datos en tiempo real con la API de Datos Abiertos de Colombia (`datos.gov.co`).
* **Gestión de Evidencia:** Almacenamiento de soportes y generación de reportes de auditoría.

## 🛠️ Tecnologías Usadas

* **Backend:** Django 5.1, Python 3.10
* **IA / OCR:** PyTorch, EasyOCR, SpaCy (NLP), PDFPlumber
* **Infraestructura:** PythonAnywhere (Deploy), WhiteNoise (Static files)
* **Frontend:** Bootstrap 5, JavaScript (Loaders y Validaciones)

## 📦 Instalación Local

1. Clonar el repositorio:
   ```bash
   git clone [https://github.com/TU_USUARIO/sistema-auditoria-soat.git](https://github.com/TU_USUARIO/sistema-auditoria-soat.git)
   ```
2. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```
3. Migrar base de datos:
   ```bash
   python manage.py migrate
   ```
4. Correr servidor:
   ```bash
   python manage.py runserver
   ```