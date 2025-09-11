import anthropic
import json
import datetime
import os
import asyncio
import subprocess
import sys
from typing import List, Dict, Any, Optional
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class EnhancedClaudeChatbot:
    def __init__(self, api_key: str, log_file: str = "chatbot_log.json"):
        """
        Chatbot mejorado con soporte para servidores MCP
        
        Args:
            api_key: Tu API key de Anthropic
            log_file: Archivo donde se guardarán los logs
        """
        self.client = anthropic.Anthropic(api_key=api_key)
        self.conversation_history: List[Dict] = []
        self.log_file = log_file
        self.session_id = self._generate_session_id()
        
        # Sesiones MCP
        self.mcp_sessions = {}
        self.available_tools = {}
        
        # Cargar logs existentes
        self._load_existing_logs()
        
    def _generate_session_id(self) -> str:
        """Genera un ID único para la sesión actual"""
        return f"session_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    def _load_existing_logs(self):
        """Carga logs existentes del archivo JSON"""
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    self.all_logs = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                self.all_logs = {}
        else:
            self.all_logs = {}
    
    async def connect_mcp_server(self, server_name: str, server_command: List[str]) -> bool:
        """
        Conecta a un servidor MCP
        
        Args:
            server_name: Nombre del servidor MCP
            server_command: Comando para iniciar el servidor
            
        Returns:
            True si la conexión fue exitosa, False en caso contrario
        """
        try:
            server_params = StdioServerParameters(
                command=server_command[0],
                args=server_command[1:] if len(server_command) > 1 else []
            )
            
            stdio_transport = await stdio_client(server_params)
            session = ClientSession(stdio_transport[0], stdio_transport[1])
            
            await session.initialize()
            
            # Listar herramientas disponibles
            tools_result = await session.list_tools()
            
            self.mcp_sessions[server_name] = session
            self.available_tools[server_name] = tools_result.tools
            
            print(f"✅ Conectado exitosamente al servidor MCP: {server_name}")
            print(f"📦 Herramientas disponibles: {[tool.name for tool in tools_result.tools]}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error conectando al servidor MCP {server_name}: {str(e)}")
            return False
    
    async def call_mcp_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Optional[str]:
        """
        Llama a una herramienta de un servidor MCP
        
        Args:
            server_name: Nombre del servidor MCP
            tool_name: Nombre de la herramienta
            arguments: Argumentos para la herramienta
            
        Returns:
            Resultado de la herramienta o None si hay error
        """
        if server_name not in self.mcp_sessions:
            return f"❌ Servidor MCP '{server_name}' no está conectado"
        
        try:
            session = self.mcp_sessions[server_name]
            result = await session.call_tool(tool_name, arguments)
            
            if result.isError:
                return f"❌ Error en herramienta {tool_name}: {result.content}"
            
            # Procesar el contenido de la respuesta
            content_str = ""
            for content in result.content:
                if hasattr(content, 'text'):
                    content_str += content.text
                else:
                    content_str += str(content)
            
            return content_str
            
        except Exception as e:
            return f"❌ Error ejecutando herramienta {tool_name}: {str(e)}"
    
    def _save_log(self, user_message: str, bot_response: str, timestamp: str):
        """Guarda la interacción en el log"""
        if self.session_id not in self.all_logs:
            self.all_logs[self.session_id] = []
        
        log_entry = {
            "timestamp": timestamp,
            "user_message": user_message,
            "bot_response": bot_response
        }
        
        self.all_logs[self.session_id].append(log_entry)
        
        with open(self.log_file, 'w', encoding='utf-8') as f:
            json.dump(self.all_logs, f, ensure_ascii=False, indent=2)
    
    def _build_conversation_context(self) -> str:
        """Construye el contexto de la conversación"""
        if not self.conversation_history:
            return ""
        
        context = "Historial de la conversación:\n"
        for entry in self.conversation_history[-10:]:
            context += f"Usuario: {entry['user']}\n"
            context += f"Asistente: {entry['assistant']}\n\n"
        
        return context
    
    def _build_mcp_tools_context(self) -> str:
        """Construye el contexto de las herramientas MCP disponibles"""
        if not self.available_tools:
            return ""
        
        context = "\nHerramientas MCP disponibles:\n"
        for server_name, tools in self.available_tools.items():
            context += f"\nServidor {server_name}:\n"
            for tool in tools:
                context += f"  - {tool.name}: {tool.description}\n"
        
        return context
    
    async def process_mcp_request(self, user_message: str) -> Optional[str]:
        """
        Procesa solicitudes que requieren herramientas MCP
        
        Args:
            user_message: Mensaje del usuario
            
        Returns:
            Resultado de las herramientas MCP o None si no se necesitan
        """
        # Detectar si el usuario solicita operaciones de archivos o git
        lower_message = user_message.lower()
        
        mcp_result = ""
        
        # Escenario: Crear repositorio, README y hacer commit
        if any(word in lower_message for word in ["repositorio", "repository", "git", "commit", "readme"]):
            if "filesystem" in self.mcp_sessions and "git" in self.mcp_sessions:
                
                # Paso 1: Crear directorio para el repositorio
                if "crear repositorio" in lower_message or "create repository" in lower_message:
                    repo_name = "mi_proyecto"
                    
                    # Crear directorio
                    mkdir_result = await self.call_mcp_tool("filesystem", "create_directory", {
                        "path": repo_name
                    })
                    mcp_result += f"📁 Creando directorio: {mkdir_result}\n"
                    
                    # Inicializar git
                    git_init_result = await self.call_mcp_tool("git", "init", {
                        "path": repo_name
                    })
                    mcp_result += f"🔧 Inicializando Git: {git_init_result}\n"
                    
                    # Crear README.md
                    readme_content = f"""# {repo_name}

Este es un proyecto creado automáticamente por el chatbot.

## Descripción
Repositorio de ejemplo creado el {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Características
- Creado automáticamente
- Con Git inicializado
- README generado

## Uso
Este es un ejemplo de demostración.
"""
                    
                    write_result = await self.call_mcp_tool("filesystem", "write_file", {
                        "path": f"{repo_name}/README.md",
                        "content": readme_content
                    })
                    mcp_result += f"📝 Creando README.md: {write_result}\n"
                    
                    # Agregar archivo al git
                    git_add_result = await self.call_mcp_tool("git", "add", {
                        "path": repo_name,
                        "files": ["README.md"]
                    })
                    mcp_result += f"➕ Agregando archivo a Git: {git_add_result}\n"
                    
                    # Hacer commit
                    git_commit_result = await self.call_mcp_tool("git", "commit", {
                        "path": repo_name,
                        "message": "Initial commit: Add README.md"
                    })
                    mcp_result += f"💾 Realizando commit: {git_commit_result}\n"
                    
                    return mcp_result
        
        # Análisis de letras de Taylor Swift
        elif "taylor swift" in lower_message or "analizar cancion" in lower_message:
            if "taylor" in self.mcp_sessions:
                # Extraer nombre de canción si se proporciona
                song_name = "Love Story"  # Por defecto
                if "cancion" in lower_message:
                    # Intentar extraer el nombre de la canción
                    words = user_message.split()
                    for i, word in enumerate(words):
                        if word.lower() in ["cancion", "song"] and i + 1 < len(words):
                            song_name = " ".join(words[i+1:])
                            break
                
                analysis_result = await self.call_mcp_tool("taylor", "analyze_song", {
                    "song_title": song_name
                })
                
                return f"🎵 Análisis de la canción '{song_name}':\n{analysis_result}"
        
        return None
    
    async def ask(self, user_message: str) -> str:
        """
        Envía una pregunta al chatbot con soporte MCP
        
        Args:
            user_message: Mensaje/pregunta del usuario
            
        Returns:
            Respuesta del chatbot
        """
        timestamp = datetime.datetime.now().isoformat()
        
        try:
            # Primero verificar si necesita herramientas MCP
            mcp_result = await self.process_mcp_request(user_message)
            
            if mcp_result:
                # Si se usaron herramientas MCP, incluir el resultado
                context = self._build_conversation_context()
                mcp_context = self._build_mcp_tools_context()
                
                full_message = f"{context}{mcp_context}\n\nResultado de herramientas MCP:\n{mcp_result}\n\nPregunta del usuario: {user_message}\n\nPor favor, explica lo que se hizo y proporciona un resumen útil."
            else:
                # Conversación normal
                context = self._build_conversation_context()
                mcp_context = self._build_mcp_tools_context()
                full_message = f"{context}{mcp_context}\n\nNueva pregunta: {user_message}"
            
            # Llamar a Claude
            response = self.client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=1500,
                temperature=0.7,
                messages=[
                    {
                        "role": "user",
                        "content": full_message
                    }
                ]
            )
            
            bot_response = response.content[0].text
            
            # Si hubo resultado MCP, agregarlo a la respuesta
            if mcp_result:
                final_response = f"{mcp_result}\n\n🤖 Claude: {bot_response}"
            else:
                final_response = bot_response
            
            # Agregar al historial
            self.conversation_history.append({
                "user": user_message,
                "assistant": final_response
            })
            
            # Guardar en log
            self._save_log(user_message, final_response, timestamp)
            
            return final_response
            
        except Exception as e:
            error_message = f"Error: {str(e)}"
            self._save_log(user_message, error_message, timestamp)
            return error_message
    
    def show_mcp_status(self):
        """Muestra el estado de las conexiones MCP"""
        print("\n" + "="*50)
        print("ESTADO DE SERVIDORES MCP")
        print("="*50)
        
        if not self.mcp_sessions:
            print("❌ No hay servidores MCP conectados")
            return
        
        for server_name, session in self.mcp_sessions.items():
            print(f"\n✅ Servidor: {server_name}")
            if server_name in self.available_tools:
                tools = self.available_tools[server_name]
                print(f"📦 Herramientas ({len(tools)}):")
                for tool in tools:
                    print(f"   - {tool.name}: {tool.description}")
    
    async def setup_mcp_servers(self):
        """Configura y conecta los servidores MCP"""
        print("🔧 Configurando servidores MCP...")
        
        # Conectar Filesystem MCP (requiere instalación)
        filesystem_success = await self.connect_mcp_server(
            "filesystem",
            ["npx", "@modelcontextprotocol/server-filesystem", "/tmp"]
        )
        
        # Conectar Git MCP (requiere instalación)  
        git_success = await self.connect_mcp_server(
            "git",
            ["npx", "@modelcontextprotocol/server-git"]
        )
        
        # Conectar nuestro servidor personalizado de Taylor Swift (FastMCP)
        taylor_success = await self.connect_mcp_server(
            "taylor",
            ["python", "C:\\Users\\Francis\\OneDrive - UVG\\Francis\\2025\\Semestre 8\\Redes\\mcp\\taylor.py"]
        )
        
        return filesystem_success, git_success, taylor_success
    
    def show_conversation_history(self):
        """Muestra el historial de la conversación actual"""
        if not self.conversation_history:
            print("No hay historial de conversación en esta sesión.")
            return
        
        print("\n" + "="*50)
        print("HISTORIAL DE CONVERSACIÓN ACTUAL")
        print("="*50)
        
        for i, entry in enumerate(self.conversation_history, 1):
            print(f"\n[{i}] Usuario: {entry['user']}")
            print(f"[{i}] Bot: {entry['assistant'][:200]}..." if len(entry['assistant']) > 200 else f"[{i}] Bot: {entry['assistant']}")
    
    async def start_interactive_session(self):
        """Inicia una sesión interactiva mejorada"""
        print("="*60)
        print("🤖 CHATBOT CLAUDE MEJORADO - SESIÓN CON MCP")
        print("="*60)
        
        # Configurar servidores MCP
        fs_ok, git_ok, taylor_ok = await self.setup_mcp_servers()
        
        print(f"\nEstado de servidores MCP:")
        print(f"   Filesystem: {'✅' if fs_ok else '❌'}")
        print(f"   Git: {'✅' if git_ok else '❌'}")
        print(f"   Taylor Swift Analyzer: {'✅' if taylor_ok else '❌'}")
        
        print("\nComandos disponibles:")
        print("- 'salir': Terminar sesión")
        print("- 'historial': Ver historial")
        print("- 'mcp': Ver estado de servidores MCP")
        print("- 'crear repositorio': Demostrar escenario Git")
        print("- 'analizar cancion [nombre]': Analizar canción de Taylor Swift")
        print("-"*60)
        
        while True:
            user_input = input("\n👤 Tú: ").strip()
            
            if user_input.lower() in ['salir', 'exit']:
                print("Cerrando conexiones MCP...")
                for session in self.mcp_sessions.values():
                    try:
                        await session.close()
                    except:
                        pass
                print("¡Hasta luego!")
                break
            elif user_input.lower() == 'historial':
                self.show_conversation_history()
                continue
            elif user_input.lower() == 'mcp':
                self.show_mcp_status()
                continue
            elif not user_input:
                continue
            
            print("\n🤖 Procesando...")
            response = await self.ask(user_input)
            print(f"\n{response}")


async def main():
    """Función principal para ejecutar el chatbot mejorado"""
    api_key = os.getenv('ANTHROPIC_API_KEY')
    
    if not api_key:
        api_key = input("Ingresa tu API key de Anthropic: ").strip()
    
    if not api_key:
        print("Se requiere una API key.")
        return
    
    try:
        chatbot = EnhancedClaudeChatbot(api_key)
        await chatbot.start_interactive_session()
        
    except Exception as e:
        print(f"Error: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())