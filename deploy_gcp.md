# ☁️ Guía de Despliegue en Google Cloud Run usando Cloud Shell (Serverless de Mínimo Costo)

Esta guía documenta la arquitectura e instrucciones paso a paso para desplegar el Webhook de WhatsApp Business API en **Google Cloud Run** ejecutando los comandos directamente desde **Google Cloud Shell** en la consola web de GCP e integrando **Google Secret Manager** para la gestión segura de credenciales.

---

## 💰 ¿Por qué Cloud Run y Cloud Shell?

- **Google Cloud Shell:** Es un entorno de terminal basado en navegador que viene con la herramienta `gcloud CLI`, `git`, `docker` y el SDK de Google Cloud preinstalados y autenticados automáticamente con tu proyecto de GCP. No requiere instalar software en tu máquina local.
- **Google Cloud Run (Serverless):**
  - **Escalado a cero (Scale to Zero):** Cuando no hay mensajes entrantes de WhatsApp, las instancias se reducen a `0` ($0.00 USD/mes).
  - **Capa Gratuita Generosa (Free Tier):** Incluye **2 millones de peticiones gratuitas al mes**, 180,000 vCPU-segundos y 360,000 GiB-segundos de memoria.
  - **SSL Automático:** Cloud Run asigna una URL con certificado **HTTPS válido gestionado por Google**, requerimiento obligatorio de Meta.

---

## 📋 Requisitos Previos

1. Tener una cuenta en [Google Cloud Console](https://console.cloud.google.com/) con un Proyecto seleccionado y Facturación habilitada.
2. Abrir **Google Cloud Shell**:
   - Haz clic en el ícono **`>_` (Activar Cloud Shell)** situado en la barra superior derecha de la consola de Google Cloud.
   - Espera unos segundos a que se aprovisione tu terminal virtual bash.

---

## 📁 Paso 1: Cargar el Código Fuente en Cloud Shell

Dentro de la terminal de Cloud Shell, clona tu repositorio o descarga el código fuente:

```bash
# Opción A: Clonar desde tu repositorio de Git
git clone https://github.com/TU_USUARIO/csa-business-agent.git
cd csa-business-agent

# Opción B: Si subiste el código comprimido en .zip desde el menú "Subir archivo" de Cloud Shell
unzip csa-business-agent.zip
cd csa-business-agent
```

---

## 🛠️ Paso 2: Configurar el Proyecto de GCP y Habilitar Servicios

En Cloud Shell (entorno Bash), define las variables de entorno para la sesión e inicializa las APIs requeridas:

```bash
# 1. Capturar el ID del proyecto activo en la sesión de Cloud Shell
export PROJECT_ID=$(gcloud config get-value project)
export REGION="us-central1"
export SERVICE_NAME="whatsapp-webhook"

# Confirmar que el proyecto activo sea el correcto
echo "Proyecto activo: $PROJECT_ID"

# 2. Habilitar las APIs necesarias en GCP
gcloud services enable \
  run.googleapis.com \
  secretmanager.googleapis.com \
  cloudbuild.googleapis.com
```

---

## 🔐 Paso 3: Guardar Credenciales en Google Secret Manager

Para evitar exponer valores sensibles como `APP_SECRET` o `WHATSAPP_TOKEN` en texto plano, crearemos secretos en **Secret Manager** usando comandos `bash`:

```bash
# 1. Crear secreto para VERIFY_TOKEN
echo -n "tu_token_de_verificacion_123" | gcloud secrets create VERIFY_TOKEN --data-file=-

# 2. Crear secreto para APP_SECRET
echo -n "tu_app_secret_de_meta" | gcloud secrets create APP_SECRET --data-file=-

# 3. Crear secreto para WHATSAPP_TOKEN
echo -n "EAABxxxx..." | gcloud secrets create WHATSAPP_TOKEN --data-file=-

# 4. Crear secreto para PHONE_NUMBER_ID
echo -n "109876543210987" | gcloud secrets create PHONE_NUMBER_ID --data-file=-
```

> 💡 **Conceder Permisos a la Cuenta de Servicio de Compute Engine:**
> Cloud Run necesita acceso a Secret Manager para leer las credenciales. Asigna el rol `Secret Manager Secret Accessor`:
> ```bash
> PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
>
> gcloud projects add-iam-policy-binding $PROJECT_ID \
>   --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
>   --role="roles/secretmanager.secretAccessor"
> ```

---

## 🚀 Paso 4: Desplegar el Servicio en Cloud Run

Ejecuta el despliegue directo desde la raíz del proyecto en Cloud Shell. Google Cloud Build compilará la aplicación utilizando el archivo `Procfile` (o `Dockerfile`) y la desplegará en Cloud Run:

```bash
gcloud run deploy $SERVICE_NAME \
  --source . \
  --region $REGION \
  --platform managed \
  --allow-unauthenticated \
  --min-instances 0 \
  --max-instances 3 \
  --memory 512Mi \
  --cpu 1 \
  --set-env-vars "DATABASE_URL=sqlite:///./whatsapp_messages.db,LOG_LEVEL=INFO" \
  --set-secrets "VERIFY_TOKEN=VERIFY_TOKEN:latest,APP_SECRET=APP_SECRET:latest,WHATSAPP_TOKEN=WHATSAPP_TOKEN:latest,PHONE_NUMBER_ID=PHONE_NUMBER_ID:latest"
```

### Explicación de los Parámetros:
- `--source .`: Indicar a Cloud Build que empaquete el directorio actual usando el `Dockerfile`.
- `--allow-unauthenticated`: Permite que Meta realice solicitudes HTTP públicas a tu Webhook.
- `--min-instances 0`: **Garantiza costo cero** cuando no hay tráfico.
- `--set-secrets`: Inyecta los secretos directamente como variables de entorno leídas por Pydantic.

Al completar el proceso, Cloud Shell mostrará la URL pública asignada:
*Ejemplo:* `https://whatsapp-webhook-a1b2c3d4-uc.a.run.app`

---

## ⚙️ Paso 5: Configurar la URL de Cloud Run en el Panel de Meta Developers

1. Copia la URL devuelta por Cloud Run y concatena la ruta `/webhook`.
   - *Ejemplo:* `https://whatsapp-webhook-a1b2c3d4-uc.a.run.app/webhook`
2. Abre la consola de [Meta Developers Dashboard](https://developers.facebook.com/apps/).
3. Ve a **WhatsApp** > **Configuración (Configuration)** > **Webhook** > **Editar (Edit)**.
4. Completa la configuración:
   - **Callback URL:** `https://whatsapp-webhook-a1b2c3d4-uc.a.run.app/webhook`
   - **Verify Token:** El valor que pusiste en el secreto `VERIFY_TOKEN` (ej. `tu_token_de_verificacion_123`).
5. Haz clic en **Verificar y guardar**.
6. En la lista de suscripciones, marca la casilla **`messages`**.

---

## 🗄️ Consideraciones sobre Persistencia de Datos (SQLite)

- En esta configuración serverless de costo mínimo, SQLite guarda la base de datos `whatsapp_messages.db` en el sistema de archivos efímero de la instancia.
- Si la instancia se escala a cero por inactividad prolongada, la base de datos se reiniciará limpia.
- **Para entornos de producción empresarial**, reemplaza la variable `DATABASE_URL` por una instancia gestionada de **Cloud SQL for PostgreSQL** o **Cloud Firestore**.

---

## 📊 Monitoreo y Logs en Producción

Puedes consultar los logs de mensajes procesados por tu Webhook directamente desde Cloud Shell ejecutando:

```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME" --limit 50
```

O desde la interfaz web de GCP navegando a **Cloud Run** > **`whatsapp-webhook`** > pestaña **Logs**.


