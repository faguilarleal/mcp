# MCP Multi-Client

Un cliente MCP mejorado que puede conectarse a múltiples servidores MCP simultáneamente usando archivos de configuración  TOML.

## Características

- Conexión a múltiples servidores MCP simultáneamente
- Configuración mediante archivos JSON o TOML
- Variables de entorno por servidor
- Habilitación/deshabilitación de servidores
- Retrocompatibilidad con modo servidor único
- Prefijo automático de herramientas por servidor
- Manejo de errores robusto

## Instalación

```bash
pip install anthropic python-dotenv mcp

# Para soporte TOML en Python < 3.11
pip install tomli
```

## Uso

### Modo Multi-Servidor (Recomendado)

```bash

# Usando archivo TOML
python client.py servers.toml
```

### Modo Servidor Único 

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



### Ejemplo TOML (servers.toml)

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
