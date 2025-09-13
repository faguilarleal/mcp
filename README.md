# MCP Multi-Client

Un cliente MCP mejorado que puede conectarse a múltiples servidores MCP simultáneamente usando archivos de configuración JSON o TOML.

## Características

- ✅ Conexión a múltiples servidores MCP simultáneamente
- ✅ Configuración mediante archivos JSON o TOML
- ✅ Variables de entorno por servidor
- ✅ Habilitación/deshabilitación de servidores
- ✅ Retrocompatibilidad con modo servidor único
- ✅ Prefijo automático de herramientas por servidor
- ✅ Manejo de errores robusto

## Instalación

```bash
pip install anthropic python-dotenv mcp

# Para soporte TOML en Python < 3.11
pip install tomli
```

## Uso

### Modo Multi-Servidor (Recomendado)

```bash
# Usando archivo JSON
python client.py servers.json

# Usando archivo TOML
python client.py servers.toml
```

### Modo Servidor Único (Retrocompatibilidad)

```bash
python client.py ./my_server.py
```

## Configuración

### Estructura del Archivo de Configuración

Cada servidor puede tener las siguientes opciones:

- **script**: Ruta al script del servidor (automáticamente detecta python/node)
- **command**: Comando para ejecutar (python, node, etc.)
- **args**: Lista de argumentos para el comando
- **env**: Variables de entorno específicas del servidor
- **enabled**: Si el servidor está habilitado (true/false)

### Ejemplo JSON (servers.json)

```json
{
  "servers": {
    "mi_servidor_local": {
      "script": "./mi_servidor.py",
      "enabled": true,
      "env": {
        "DEBUG": "1",
        "API_KEY": "tu_api_key_aqui"
      }
    },
    "servidor_weather": {
      "command": "python",
      "args": ["./weather_server.py"],
      "enabled": true
    }
  }
}
```

### Ejemplo TOML (servers.toml)

```toml
[servers.mi_servidor_local]
script = "./mi_servidor.py"
enabled = true

[servers.mi_servidor_local.env]
DEBUG = "1"
API_KEY = "tu_api_key_aqui"

[servers.servidor_weather]
command = "python"
args = ["./weather_server.py"]
enabled = true
```

## Comandos Interactivos

Una vez iniciado el cliente, puedes usar:

- **Consultas normales**: Escribe tu pregunta y Claude usará las herramientas disponibles
- **`list`**: Muestra todos los servidores conectados y sus herramientas
- **`quit`**: Sale del programa

## Manejo de Herramientas

Las herramientas de diferentes servidores se prefijan automáticamente con el nombre del servidor:

- Servidor "weather" con herramienta "get_forecast" → "weather.get_forecast"
- Servidor "files" con herramienta "read_file" → "files.read_file"

Esto evita conflictos entre herramientas con el mismo nombre de diferentes servidores.

## Variables de Entorno

Crea un archivo `.env` en el directorio del proyecto:

```
ANTHROPIC_API_KEY=tu_clave_anthropic_aqui
```

## Casos de Uso Comunes

### 1. Servidor Local + Herramientas Remotas

```json
{
  "servers": {
    "local_dev": {
      "script": "./mi_servidor_desarrollo.py",
      "enabled": true
    },
    "production_tools": {
      "command": "python",
      "args": ["-m", "production_mcp_server"],
      "enabled": true
    }
  }
}
```

### 2. Diferentes Lenguajes

```json
{
  "servers": {
    "python_tools": {
      "script": "./python_server.py",
      "enabled": true
    },
    "node_tools": {
      "script": "./node_server.js",
      "enabled": true
    }
  }
}
```

### 3. Configuración de Desarrollo vs Producción

```json
{
  "servers": {
    "database": {
      "script": "./db_server.py",
      "enabled": true,
      "env": {
        "DB_URL": "postgresql://localhost/dev_db",
        "DEBUG": "1"
      }
    },
    "cache": {
      "script": "./cache_server.py",
      "enabled": false
    }
  }
}
```

## Manejo de Errores

El cliente maneja graciosamente:

- Servidores que no se pueden conectar (continúa con los otros)
- Herramientas que fallan (reporta error y continúa)
- Archivos de configuración malformados
- Servidores que se desconectan durante la ejecución

## Estructura del Proyecto

```
proyecto/
├── client.py              # Cliente principal
├── servers.json          # Configuración de servidores
├── .env                  # Variables de entorno
├── mi_servidor.py        # Tu servidor local
└── otros_servidores/     # Otros servidores MCP
```