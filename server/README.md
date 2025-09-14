# Taylor Swift MCP Analysis Server 🎵

Un servidor MCP (Model Context Protocol) especializado en el análisis de canciones de Taylor Swift. Proporciona herramientas para obtener letras, realizar análisis emocional y comparar canciones.

##  Características

- **Obtención de letras**: Descarga letras de canciones de Taylor Swift
- **Análisis emocional**: Analiza sentimientos, vocabulario y características musicales
- **Comparación de canciones**: Compara dos canciones en múltiples dimensiones
- **Estadísticas rápidas**: Obtén métricas básicas sin análisis completo
- **Respeto de copyright**: Solo muestra previews de letras, análisis completo sin reproducir contenido

##  Instalación y Configuración

### Dependencias

Correr en ambiente virtual
```bash
pip install requirements.txt
```



##  Formas de Ejecutar el Servidor



###  Modo MCP Cliente Único

```bash
python client.py ./server.py
```

### 3. Modo Multi-Servidor (Recomendado)

Crea un archivo de configuración `servers.json`:

Asegurate de tener configurado un .toml
Luego ejecuta:

```bash
python client.py config.toml
```

##  Integración con Otros Servidores MCP

### Configuración Multi-Servidor Completa

Aquí tienes ejemplos de cómo combinar tu servidor de Taylor Swift con otros servidores MCP:

#### Archivo `multi_servers.toml`:

```toml
[servers.local_server]
script = "../../server/server.py"
enabled = true

[servers.git]
command = "python"
args = ["-m", "mcp_server_git", "--repository", "../../"]
enabled = true

[servers.filesystem]
command = "mcp-server-filesystem"
args = ["../../"]
enabled = true
```




##  Herramientas Disponibles

Tu servidor MCP expone las siguientes herramientas que otros clientes pueden usar:

### 1. `get_song_lyrics`
- **Descripción**: Obtiene las letras de una canción de Taylor Swift
- **Parámetros**: `song_title` (string)
- **Retorna**: Preview de letras y confirmación de obtención completa

### 2. `analyze_song`
- **Descripción**: Análisis completo de una canción (emocional, estadístico, características)
- **Parámetros**: `song_title` (string)
- **Retorna**: Reporte detallado de análisis

### 3. `compare_songs`
- **Descripción**: Compara dos canciones de Taylor Swift
- **Parámetros**: `song1` (string), `song2` (string)
- **Retorna**: Análisis comparativo detallado

### 4. `get_song_stats_only`
- **Descripción**: Estadísticas básicas sin análisis completo
- **Parámetros**: `song_title` (string)
- **Retorna**: Métricas rápidas



## 🔌 Cómo Otros Pueden Usar mi Servidor

### Para Desarrolladores que Quieren Integrar el Servidor:

#### 1. Instalación Directa

```bash
git clone https://github.com/faguilarleal/mcp.git
cd server
pip install -r requirements.txt
```


## Ejemplos de Consultas

Una vez conectado, puedes hacer consultas como:

```bash
# Análisis simple
"Analiza la canción 'Anti-Hero'"

# Comparación
"Compara 'Cruel Summer' con 'Paper Rings'"

# Estadísticas
"Dame las estadísticas rápidas de 'Cardigan'"

# Multi-servidor (ejemplo con servidor de archivos)
"Analiza 'Willow' y guarda el resultado en analysis_results.txt"

# Multi-servidor (ejemplo con base de datos)
"Compara 'August' con 'Betty' y almacena los resultados en la base de datos"
```



### Desarrollo Local

Para desarrollo por medio de stdio:

```toml
[servers.local_server]
script = "<ruta>/server.py"
enabled = false
```

### Conexión remota 

La conección es por medio de sse    

Para este proyecto se utilizo un ec2 de aws 

1. Clonar el repositorio en el servidor remoto 
ip publica: 34.201.103.76
encontrar el key en server\KeyTaylor.ppk para poder ingresar en el puerto 22 via ssh
```bash
uv venv
source .venv/bin/activate
uv add "mcp[cli]" httpx
uv add fastmcp
uv run server.py
```

2. Luego en tu computadora donde tienes clonado el cliente ejecuta

```bash
python client.py http://34.201.103.76:8000/sse
```