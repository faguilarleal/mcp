# Taylor Swift MCP Analysis Server 🎵

Un servidor MCP (Model Context Protocol) especializado en el análisis de canciones de Taylor Swift. Proporciona herramientas para obtener letras, realizar análisis emocional y comparar canciones.

## 📋 Características

- **Obtención de letras**: Descarga letras de canciones de Taylor Swift
- **Análisis emocional**: Analiza sentimientos, vocabulario y características musicales
- **Comparación de canciones**: Compara dos canciones en múltiples dimensiones
- **Estadísticas rápidas**: Obtén métricas básicas sin análisis completo
- **Respeto de copyright**: Solo muestra previews de letras, análisis completo sin reproducir contenido

## 🛠️ Instalación y Configuración

### Dependencias

```bash
pip install fastmcp httpx asyncio
```

### Variables de Entorno (Opcionales)

Crea un archivo `.env` si necesitas configuraciones específicas:

```bash
# Para modo HTTP (opcional)
PORT=8080
DEBUG=true
```

## 🚀 Formas de Ejecutar el Servidor

### 1. Modo Standalone (Desarrollo)

```bash
python server.py
```

### 2. Modo MCP Cliente Único

```bash
python client.py server.py
```

### 3. Modo Multi-Servidor (Recomendado)

Crea un archivo de configuración `servers.json`:

```json
{
  "servers": {
    "taylor_swift": {
      "script": "./server.py",
      "enabled": true,
      "env": {
        "DEBUG": "1"
      }
    }
  }
}
```

Luego ejecuta:

```bash
python client.py servers.json
```

## 🔧 Integración con Otros Servidores MCP

### Configuración Multi-Servidor Completa

Aquí tienes ejemplos de cómo combinar tu servidor de Taylor Swift con otros servidores MCP:

#### Archivo `multi_servers.json`:

```json
{
  "servers": {
    "taylor_swift": {
      "script": "./server.py",
      "enabled": true,
      "env": {
        "DEBUG": "1"
      }
    },
    "file_manager": {
      "command": "python",
      "args": ["-m", "mcp_server_files"],
      "enabled": true
    },
    "web_scraper": {
      "script": "./web_scraper_server.py",
      "enabled": true
    },
    "database_tools": {
      "command": "node",
      "args": ["./db_server.js"],
      "enabled": true,
      "env": {
        "NODE_ENV": "production",
        "DB_URL": "postgresql://localhost/music_db"
      }
    },
    "spotify_api": {
      "command": "python",
      "args": ["./spotify_server.py"],
      "enabled": true,
      "env": {
        "SPOTIFY_CLIENT_ID": "tu_client_id",
        "SPOTIFY_CLIENT_SECRET": "tu_client_secret"
      }
    }
  }
}
```

#### Archivo `multi_servers.toml`:

```toml
[servers.taylor_swift]
script = "./server.py"
enabled = true

[servers.taylor_swift.env]
DEBUG = "1"

[servers.file_manager]
command = "python"
args = ["-m", "mcp_server_files"]
enabled = true

[servers.web_scraper]
script = "./web_scraper_server.py"
enabled = true

[servers.database_tools]
command = "node"
args = ["./db_server.js"]
enabled = true

[servers.database_tools.env]
NODE_ENV = "production"
DB_URL = "postgresql://localhost/music_db"

[servers.spotify_api]
command = "python"
args = ["./spotify_server.py"]
enabled = true

[servers.spotify_api.env]
SPOTIFY_CLIENT_ID = "tu_client_id"
SPOTIFY_CLIENT_SECRET = "tu_client_secret"
```

### Ejecutar Multi-Servidor

```bash
python client.py multi_servers.json
```

## 🎯 Herramientas Disponibles

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

## 💡 Casos de Uso en Multi-Servidor

### Ejemplo 1: Análisis Musical Completo

Combina tu servidor con otros para análisis integral:

```bash
# Con servidor de archivos + Taylor Swift
"Analiza 'Love Story' y guarda el resultado en un archivo CSV"
# Usa: taylor_swift.analyze_song + file_manager.write_file
```

### Ejemplo 2: Investigación Musical

```bash
# Con servidor web + base de datos + Taylor Swift
"Busca información adicional sobre 'Shake It Off' en Wikipedia y compárala con mi análisis"
# Usa: web_scraper.get_content + taylor_swift.analyze_song + database_tools.save_analysis
```

### Ejemplo 3: Análisis de Tendencias

```bash
# Con múltiples APIs musicales
"Compara las características emocionales de 'Folklore' vs 'Red' usando tanto mi análisis como datos de Spotify"
# Usa: taylor_swift.compare_songs + spotify_api.get_audio_features
```

## 🔌 Cómo Otros Pueden Usar Tu Servidor

### Para Desarrolladores que Quieren Integrar tu Servidor:

#### 1. Instalación Directa

```bash
git clone tu_repositorio
cd taylor-swift-mcp
pip install -r requirements.txt
```

#### 2. Configuración en su Cliente MCP

```json
{
  "servers": {
    "taylor_analysis": {
      "script": "/ruta/a/tu/server.py",
      "enabled": true
    },
    "sus_otros_servidores": {
      "script": "./su_servidor.py",
      "enabled": true
    }
  }
}
```

#### 3. Como Paquete (Futuro)

```bash
pip install taylor-swift-mcp
```

```json
{
  "servers": {
    "taylor_swift": {
      "command": "python",
      "args": ["-m", "taylor_swift_mcp"],
      "enabled": true
    }
  }
}
```

## 📊 Ejemplos de Consultas

Una vez conectado en modo multi-servidor, puedes hacer consultas como:

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

## ⚙️ Configuración Avanzada

### Desarrollo Local

Para desarrollo y testing:

```json
{
  "servers": {
    "taylor_swift_dev": {
      "script": "./server.py",
      "enabled": true,
      "env": {
        "DEBUG": "1",
        "LOG_LEVEL": "DEBUG"
      }
    }
  }
}
```

### Producción

Para uso en producción:

```json
{
  "servers": {
    "taylor_swift_prod": {
      "script": "./server.py",
      "enabled": true,
      "env": {
        "LOG_LEVEL": "INFO",
        "CACHE_ENABLED": "true"
      }
    }
  }
}
```

### Con Rate Limiting

```json
{
  "servers": {
    "taylor_swift": {
      "script": "./server.py",
      "enabled": true,
      "env": {
        "RATE_LIMIT_REQUESTS": "60",
        "RATE_LIMIT_WINDOW": "300"
      }
    }
  }
}
```

## 🐛 Troubleshooting

### Problemas Comunes

1. **Error de conexión a API**
   ```bash
   # Verifica conectividad
   curl "https://api.lyrics.ovh/v1/Taylor%20Swift/Love%20Story"
   ```

2. **Servidor no inicia**
   ```bash
   # Verifica dependencias
   pip install --upgrade fastmcp httpx
   ```

3. **Herramientas no aparecen en cliente**
   ```bash
   # Verifica que el servidor esté en la configuración
   python client.py servers.json
   # Luego usa el comando 'list' para ver herramientas disponibles
   ```

## 📝 API Reference

### Estructura de Respuestas

#### Análisis Completo
```json
{
  "basic_stats": {
    "total_words": 234,
    "unique_words": 156,
    "lines_count": 32,
    "vocabulary_density_percent": 66.67
  },
  "emotional_analysis": {
    "positive_words_count": 8,