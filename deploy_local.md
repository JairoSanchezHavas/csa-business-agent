# 💻 Guía de Despliegue Local con Docker y Túnel HTTPS (Windows 11)

Esta guía detalla paso a paso cómo ejecutar el Webhook de WhatsApp Business API en tu entorno local usando **Docker Desktop** en Windows 11 y cómo exponer tu puerto local a internet mediante un túnel HTTPS con **ngrok** o **Cloudflare Tunnels (cloudflared)** para conectar exitosamente con el App Dashboard de Meta Developers.

---

## 📋 Requisitos Previos

Antes de comenzar, asegúrate de tener instalado y configurado:

1. **Docker Desktop para Windows:**
   - [Descargar Docker Desktop](https://www.docker.com/products/docker-desktop/) con soporte para WSL 2 habilitado.
2. **Cuenta de Meta Developers:**
   - Registrarte en [Meta for Developers](https://developers.facebook.com/).
   - Crear una aplicación de tipo **Business** o **Other** y agregar el producto **WhatsApp**.
3. **Una herramienta de Túnel HTTPS:**
   - **Opción A:** [ngrok](https://ngrok.com/) (Requiere cuenta gratuita).
   - **Opción B:** [cloudflared](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/get-started/) (Gratuito, sin registro obligatorio).

---

## 🚀 Paso 1: Configurar las Variables de Entorno

1. Abre una terminal de **PowerShell** o **Símbolo del sistema (CMD)** en la raíz del proyecto `csa-business-agent`.
2. Crea el archivo `.env` duplicando `.env.example`:

   **En PowerShell:**
   ```powershell
   Copy-Item .env.example .env
   ```

   **En CMD:**
   ```cmd
   copy .env.example .env
   ```

3. Abre el archivo `.env` en VS Code o tu editor preferido y completa las variables:

```env
VERIFY_TOKEN=mi_token_de_prueba_local_123
APP_SECRET=tu_app_secret_de_meta
WHATSAPP_TOKEN=EAABxxxx...
PHONE_NUMBER_ID=109876543210987
DATABASE_URL=sqlite:///./whatsapp_messages.db
LOG_LEVEL=INFO
```

> **¿Dónde encuentro estos datos en Meta?**
> - **`APP_SECRET`:** Configuración de la app > Básica > Clave secreta de la aplicación.
> - **`WHATSAPP_TOKEN`:** WhatsApp > API Setup > Temporary access token.
> - **`PHONE_NUMBER_ID`:** WhatsApp > API Setup > Phone number ID.
> - **`VERIFY_TOKEN`:** Un texto libre inventado por ti (ejemplo: `mi_token_de_prueba_local_123`).

---

## 🐳 Paso 2: Construir y Ejecutar el Contenedor Docker

> 📌 **¿Dónde ejecutar estos comandos?**  
> Abre una terminal de **PowerShell** o **Símbolo del sistema (CMD)** en tu máquina Windows y **ubícate en la carpeta raíz del proyecto** (`csa-business-agent`), donde se encuentran los archivos `Dockerfile` y `.env`.  
> *Ejemplo:* `cd C:\Users\tu_usuario\csa-business-agent`

1. **Construir la imagen de Docker:**
   *(El punto `.` al final indica a Docker que use el `Dockerfile` ubicado en el directorio actual)*

```powershell
docker build -t whatsapp-webhook:v1 .
```

2. **Ejecutar el contenedor montando el archivo `.env` y el puerto `8000`:**

   * **En PowerShell** (usa el acento grave ``` ` ``` para saltos de línea):
     ```powershell
     docker run -d `
       --name whatsapp-app `
       -p 8000:8000 `
       --env-file .env `
       whatsapp-webhook:v1
     ```

   * **En CMD / Símbolo del Sistema** (usa el acento circunflejo `^` para saltos de línea):
     ```cmd
     docker run -d ^
       --name whatsapp-app ^
       -p 8000:8000 ^
       --env-file .env ^
       whatsapp-webhook:v1
     ```

   * **Comando universal en una sola línea** (funciona exactamente igual en PowerShell, CMD, Git Bash y Linux):
     ```bash
     docker run -d --name whatsapp-app -p 8000:8000 --env-file .env whatsapp-webhook:v1
     ```

3. **Verificar que el contenedor esté corriendo y consultar los logs:**

```powershell
docker ps
docker logs -f whatsapp-app
```

Deberías ver en los logs algo similar a:
```text
2026-09-02 10:00:00 [INFO] whatsapp-webhook: Iniciando aplicacion y creando base de datos SQLite...
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

4. **Probar el acceso local en tu navegador:**
   - Abre [http://localhost:8000/dashboard](http://localhost:8000/dashboard) en tu navegador. Deberías ver la interfaz web del Dashboard de monitoreo.

---

## 🌐 Paso 3: Exponer el Localhost mediante Túnel HTTPS

Meta exige estrictamente que la URL del Webhook sea accesible vía **HTTPS** con un certificado SSL válido. El puerto `localhost:8000` no es accesible desde los servidores de Meta en internet.

Elige **una** de las dos opciones siguientes:

### Opción A: Usar ngrok (Recomendado)

1. Instala ngrok vía WinGet o descárgalo desde su web oficial:
   ```powershell
   winget install ngrok.ngrok
   ```
2. Autentica ngrok con tu token de la consola (solo la primera vez):
   ```powershell
   ngrok config add-authtoken TU_AUTHTOKEN_DE_NGROK
   ```
3. Inicia el túnel apuntando al puerto `8000`:
   ```powershell
   ngrok http 8000
   ```
4. Copia la URL pública generada que empieza con `https://` (ejemplo: `https://a1b2-201-123-45-67.ngrok-free.app`).

### Opción B: Usar Cloudflare Tunnel (`cloudflared`)

1. Instala `cloudflared` vía WinGet:
   ```powershell
   winget install Cloudflare.cloudflared
   ```
2. Inicia un túnel rápido y gratuito:
   ```powershell
   cloudflared tunnel --url http://localhost:8000
   ```
3. En la consola busca la URL pública generada con dominio `.trycloudflare.com` (ejemplo: `https://subdominio-aleatorio.trycloudflare.com`).

---

## ⚙️ Paso 4: Configurar el Webhook en el Panel de Meta Developers

1. Ve a la consola de [Meta Developers Dashboard](https://developers.facebook.com/apps/).
2. Selecciona tu aplicación.
3. En el menú lateral izquierdo, ve a **WhatsApp** > **Configuración (Configuration)**.
4. En la sección **Webhook**, haz clic en **Editar (Edit)**.
5. Configura los campos:
   - **URL de la devolución de llamada (Callback URL):** Pega la URL de tu túnel HTTPS agregando la ruta `/webhook`.
     - *Ejemplo con ngrok:* `https://a1b2-201-123-45-67.ngrok-free.app/webhook`
     - *Ejemplo con cloudflared:* `https://subdominio-aleatorio.trycloudflare.com/webhook`
   - **Identificador de verificación (Verify Token):** Escribe exactamente el mismo valor que pusiste en la variable `VERIFY_TOKEN` de tu archivo `.env` (ejemplo: `mi_token_de_prueba_local_123`).
6. Haz clic en **Verificar y guardar (Verify and Save)**.

> ⚡ **¿Qué ocurre internamente en este momento?**
> Meta enviará inmediatamente una solicitud `GET /webhook` a tu túnel. Tu servidor FastAPI verificará el token y responderá con el `hub.challenge`. Si coincide, Meta mostrará una palomita verde de éxito.

7. **Suscribirse a los eventos de mensajes:**
   - En la lista de campos del Webhook, busca el campo **`messages`** y haz clic en **Suscribirse (Subscribe)**.

---

## 🧪 Paso 5: Probar el Envío y Recepción de Mensajes

### 1. Probar Recepción de Mensaje Entrante (Inbound)
1. Toma tu teléfono móvil personal y envía un mensaje de texto por WhatsApp al número telefónico de prueba proporcionado por Meta (en la pestaña *API Setup*).
2. Revisa la consola de tu terminal donde corre Docker:
   - Verás los logs de verificación de firma HMAC-SHA256 exitosa.
3. Refresca la vista de tu navegador en [http://localhost:8000/dashboard](http://localhost:8000/dashboard).
   - Verás el mensaje entrante registrado en la tabla con la dirección **Entrante**, el número del remitente y la estampa de tiempo.

### 2. Probar Envío de Mensaje Saliente (Outbound)
1. En la vista `/dashboard`, dirígete al formulario **"Enviar Mensaje (Test)"**.
2. Ingresa tu número de teléfono personal (incluyendo el código de país sin el símbolo `+`, por ejemplo `5215512345678`).
3. Escribe un mensaje de prueba y haz clic en **Enviar por WhatsApp**.
4. Recibirás el mensaje en tu WhatsApp personal en cuestión de segundos y la tabla del Dashboard se actualizará registrando el mensaje como **Saliente**.

---

## 🛠️ Comandos Útiles de Mantenimiento

> 📌 Todos los siguientes comandos de Docker se ejecutan desde la terminal en la raíz del proyecto (`csa-business-agent`).

- **Detener el contenedor:**
  ```bash
  docker stop whatsapp-app
  ```
- **Eliminar el contenedor:**
  ```bash
  docker rm whatsapp-app
  ```
- **Reconstruir y reiniciar tras hacer cambios en el código:**

  * **En PowerShell:**
    ```powershell
    docker stop whatsapp-app ; docker rm whatsapp-app
    docker build -t whatsapp-webhook:v1 .
    docker run -d --name whatsapp-app -p 8000:8000 --env-file .env whatsapp-webhook:v1
    ```

  * **En CMD:**
    ```cmd
    docker stop whatsapp-app && docker rm whatsapp-app
    docker build -t whatsapp-webhook:v1 .
    docker run -d --name whatsapp-app -p 8000:8000 --env-file .env whatsapp-webhook:v1
    ```

