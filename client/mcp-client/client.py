import asyncio
import json
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from contextlib import AsyncExitStack

from mcp.client.sse import sse_client
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from anthropic import Anthropic
from dotenv import load_dotenv
import tomllib


load_dotenv()
MODEL = "claude-sonnet-4-20250514"

class ConversationContext:
    """Maneja el contexto de la conversación"""
    
    def __init__(self):
        self.conversation_id = str(uuid.uuid4())[:12]
        self.messages = []
        self.max_context_messages = 10  # Mantener últimos 10 intercambios
    
    def add_user_message(self, content: str):
        """Añade mensaje del usuario"""
        self.messages.append({
            "role": "user",
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        self._trim_context()
    
    def add_assistant_message(self, content: str, tools_used: List[str] = None):
        """Añade mensaje del asistente"""
        message = {
            "role": "assistant", 
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        if tools_used:
            message["tools_used"] = tools_used
        
        self.messages.append(message)
        self._trim_context()
    
    def _trim_context(self):
        """Mantiene solo los últimos N mensajes para no sobrecargar el contexto"""
        if len(self.messages) > self.max_context_messages * 2:  # user + assistant = 2 mensajes
            self.messages = self.messages[-(self.max_context_messages * 2):]
    
    def get_context_for_claude(self) -> List[Dict]:
        """Obtiene el contexto formateado para Claude"""
        context_messages = []
        for msg in self.messages:
            if msg["role"] in ["user", "assistant"]:
                context_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        return context_messages
    
    def get_summary(self) -> str:
        """Obtiene un resumen de la conversación actual"""
        if not self.messages:
            return f"Conversación {self.conversation_id}: Sin mensajes"
        
        user_msgs = len([m for m in self.messages if m["role"] == "user"])
        assistant_msgs = len([m for m in self.messages if m["role"] == "assistant"])
        
        return f"""
=== Conversación Actual: {self.conversation_id} ===
• Mensajes del usuario: {user_msgs}
• Respuestas del asistente: {assistant_msgs}
• Total de mensajes: {len(self.messages)}
• Iniciada: {self.messages[0]["timestamp"] if self.messages else "N/A"}
"""

    def clear(self):
        """Limpia la conversación actual y crea una nueva"""
        self.conversation_id = str(uuid.uuid4())[:12]
        self.messages = []

class InteractionLogger:
    """Maneja el logging de todas las interacciones"""
    
    def __init__(self, log_file: str = "mcp_interactions.txt"):
        self.log_file = Path(log_file)
        self.ensure_log_file()
    
    def ensure_log_file(self):
        """Asegura que el archivo de log existe"""
        if not self.log_file.exists():
            self.log_file.touch()
    
    def _write_log(self, level: str, message: str, conversation_id: str = None):
        """Escribe una entrada en el log"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conv_id = f"[{conversation_id}]" if conversation_id else ""
        log_entry = f"[{timestamp}] {level} {conv_id} {message}\n"
        
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)
        
        # También mostrar en consola para INFO
        if level == "INFO":
            print(f"📝 {message}")
    
    def log_startup(self, message: str):
        """Log de inicio del sistema"""
        self._write_log("STARTUP", message)
    
    def log_server_connection(self, server_name: str, status: str, tools: List[str] = None):
        """Log de conexión a servidor"""
        if tools:
            message = f"Server {server_name}: {status} - Tools: {', '.join(tools)}"
        else:
            message = f"Server {server_name}: {status}"
        self._write_log("SERVER", message)
    
    def log_user_query(self, query: str, conversation_id: str):
        """Log de consulta del usuario"""
        self._write_log("USER_QUERY", f"'{query}'", conversation_id)
    
    def log_assistant_response(self, response: str, conversation_id: str, tools_used: List[str] = None):
        """Log de respuesta del asistente"""
        tools_info = f" (Tools used: {', '.join(tools_used)})" if tools_used else ""
        # Truncar respuesta larga para el log
        truncated_response = response[:200] + "..." if len(response) > 200 else response
        self._write_log("ASSISTANT", f"'{truncated_response}'{tools_info}", conversation_id)
    
    def log_tool_call(self, tool_name: str, server_name: str, args: Dict, success: bool, conversation_id: str):
        """Log de llamada a herramienta"""
        status = "SUCCESS" if success else "FAILED"
        self._write_log("TOOL_CALL", f"{tool_name}@{server_name} {status} - Args: {json.dumps(args)}", conversation_id)
    
    def log_error(self, error: Exception, context: str, conversation_id: str = None):
        """Log de error"""
        self._write_log("ERROR", f"{context}: {str(error)}", conversation_id)
    
    def log_shutdown(self):
        """Log de cierre del sistema"""
        self._write_log("SHUTDOWN", "MCP Client shutting down")
    
    def get_recent_logs(self, lines: int = 50) -> str:
        """Obtiene las líneas más recientes del log"""
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
            
            recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
            
            if not recent_lines:
                return "No hay logs disponibles"
            
            return f"=== Últimos {len(recent_lines)} logs ===\n" + "".join(recent_lines)
        
        except Exception as e:
            return f"Error leyendo logs: {str(e)}"

class ServerConfig:
    """Configuration for a single MCP server"""
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.command = config.get('command', 'python')
        self.args = config.get('args', [])
        self.env = config.get('env', {})
        self.enabled = config.get('enabled', True)
        
        # Handle script path if provided as a single argument
        if 'script' in config:
            if isinstance(config['script'], str):
                self.args = [config['script']] + self.args
        
        # Auto-detect command based on file extension if script is provided
        if self.args and not config.get('command'):
            script_path = self.args[0]
            if script_path.endswith('.py'):
                self.command = 'python'
            elif script_path.endswith('.js'):
                self.command = 'node'
    
    def to_server_params(self) -> StdioServerParameters:
        """Convert to MCP server parameters"""
        return StdioServerParameters(
            command=self.command,
            args=self.args,
            env=self.env if self.env else None
        )

class MCPMultiClient:
    def __init__(self):
        self.sessions: Dict[str, ClientSession] = {}
        self.exit_stack = AsyncExitStack()
        self.anthropic = Anthropic()
        self.available_tools: List[Dict] = []
        
        # Inicializar contexto y logging
        self.context = ConversationContext()
        self.logger = InteractionLogger()
        
        # Log de inicio
        self.logger.log_startup("MCP Multi-Client initialized")
        
    def load_config(self, config_path: str) -> Dict[str, ServerConfig]:
        """Load server configuration from JSON or TOML file"""
        config_file = Path(config_path)
        
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        # Determine file type and load accordingly
        if config_file.suffix.lower() == '.json':
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
        elif config_file.suffix.lower() in ['.toml', '.tml']:
            if tomllib is None:
                raise ImportError("TOML support requires 'tomli' package. Install with: pip install tomli")
            with open(config_file, 'rb') as f:
                config_data = tomllib.load(f)
        else:
            raise ValueError(f"Unsupported configuration file format: {config_file.suffix}")
        
        # Parse server configurations
        servers = {}
        servers_config = config_data.get('servers', {})
        
        for server_name, server_config in servers_config.items():
            servers[server_name] = ServerConfig(server_name, server_config)
        
        return servers
    
    async def connect_to_servers(self, config_path: str):
        """Connect to all enabled servers from configuration"""
        servers_config = self.load_config(config_path)
        
        connected_servers = []
        
        for server_name, server_config in servers_config.items():
            if not server_config.enabled:
                self.logger.log_server_connection(server_name, "SKIPPED - disabled")
                continue
                
            try:
                server_params = server_config.to_server_params()
                stdio_transport = await self.exit_stack.enter_async_context(
                    stdio_client(server_params)
                )
                stdio, write = stdio_transport
                
                session = await self.exit_stack.enter_async_context(
                    ClientSession(stdio, write)
                )
                await session.initialize()
                
                self.sessions[server_name] = session
                connected_servers.append(server_name)
                
                # Get tools from this server
                response = await session.list_tools()
                server_tools = []
                tool_names = []
                
                for tool in response.tools:
                    tool_info = {
                        "name": f"{tool.name}",
                        "description": f"[{server_name}] {tool.description}",
                        "input_schema": tool.inputSchema,
                        "_server": server_name,
                        "_original_name": tool.name
                    }
                    server_tools.append(tool_info)
                    self.available_tools.append(tool_info)
                    tool_names.append(tool.name)
                
                self.logger.log_server_connection(server_name, "CONNECTED", tool_names)
                
            except Exception as e:
                self.logger.log_server_connection(server_name, f"FAILED - {str(e)}")
        
        if not connected_servers:
            raise RuntimeError("No servers could be connected")
        
        print(f"✅ Successfully connected to {len(connected_servers)} server(s)")
        print(f"🔧 Total available tools: {len(self.available_tools)}")
    
    async def connect_to_single_server(self, server_url: str = "http://127.0.0.1:8000/sse"):
        """Connect to a single SSE server (backward compatibility)"""
        headers = {
            'Accept': 'text/event-stream',
            'Cache-Control': 'no-cache'
        }
        
        try:
            sse_transport = await self.exit_stack.enter_async_context(
                sse_client(server_url, headers=headers)
            )
            read, write = sse_transport
            
            session = await self.exit_stack.enter_async_context(
                ClientSession(read, write)
            )
            await session.initialize()
            
            server_name = "taylor"  # Default server name
            self.sessions[server_name] = session

            # Get tools
            response = await session.list_tools()
            tool_names = []
            for tool in response.tools:
                self.available_tools.append({
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema,
                    "_server": server_name,
                    "_original_name": tool.name
                })
                tool_names.append(tool.name)

            self.logger.log_server_connection(server_name, "CONNECTED", tool_names)
            
        except Exception as e:
            self.logger.log_server_connection("taylor", f"FAILED - {str(e)}")
            raise

    async def process_query(self, query: str) -> str:
        """Process a query using Claude and available tools with full context"""
        import copy
        
        start_time = time.time()
        tools_used = []
        
        # Log de la consulta del usuario
        self.logger.log_user_query(query, self.context.conversation_id)
        self.context.add_user_message(query)

        # Obtener contexto completo de la conversación
        messages = self.context.get_context_for_claude()

        # Prepara herramientas para Claude
        claude_tools = []
        for tool in self.available_tools:
            valid_name = tool["name"].replace(".", "_")
            claude_tool = {
                "name": valid_name,
                "description": tool["description"],
                "input_schema": tool["input_schema"]
            }
            claude_tools.append(claude_tool)

        try:
            # Llamada inicial a Claude con contexto completo
            response = self.anthropic.messages.create(
                model=MODEL,
                max_tokens=1500,
                messages=messages,
                tools=claude_tools
            )

            final_text = []
            assistant_message_content = []

            # Procesa la respuesta de Claude
            for content in response.content:
                if content.type == "text":
                    final_text.append(content.text)
                    assistant_message_content.append(content)

                elif content.type == "tool_use":
                    tool_name = content.name
                    tool_args = content.input

                    # Busca la herramienta correcta en available_tools
                    tool_info = next((t for t in self.available_tools if t["name"] == tool_name), None)

                    if not tool_info:
                        error_msg = f"[Error: Tool {tool_name} not found]"
                        final_text.append(error_msg)
                        self.logger.log_error(
                            Exception(f"Tool not found: {tool_name}"), 
                            "tool_lookup", 
                            self.context.conversation_id
                        )
                        continue

                    server_name = tool_info["_server"]
                    original_tool_name = tool_info["_original_name"]
                    tools_used.append(f"{tool_name}@{server_name}")

                    # Llamada segura al servidor
                    try:
                        session = self.sessions[server_name]
                        result = await session.call_tool(original_tool_name, tool_args)

                        # Log de la llamada exitosa
                        self.logger.log_tool_call(
                            tool_name, server_name, tool_args, True, self.context.conversation_id
                        )

                        final_text.append(f"[✅ Called {tool_name} on {server_name}]")

                        # Actualiza mensajes para Claude con el resultado del tool
                        assistant_message_content.append(content)
                        messages.append({
                            "role": "assistant",
                            "content": copy.deepcopy(assistant_message_content)
                        })
                        messages.append({
                            "role": "user",
                            "content": [{
                                "type": "tool_result",
                                "tool_use_id": content.id,
                                "content": result.content
                            }]
                        })

                        # Obtener siguiente respuesta de Claude
                        response = self.anthropic.messages.create(
                            model=MODEL,
                            max_tokens=1500,
                            messages=messages,
                            tools=claude_tools
                        )

                        if response.content and response.content[0].text:
                            final_text.append(response.content[0].text)

                    except Exception as e:
                        error_msg = f"[❌ Error calling {tool_name}: {str(e)}]"
                        final_text.append(error_msg)
                        
                        # Log del error
                        self.logger.log_tool_call(
                            tool_name, server_name, tool_args, False, self.context.conversation_id
                        )
                        self.logger.log_error(e, f"tool_call_{tool_name}", self.context.conversation_id)

            response_text = "\n".join(final_text)
            
            # Registrar respuesta en contexto
            self.context.add_assistant_message(response_text, tools_used)
            
            # Log de la respuesta
            self.logger.log_assistant_response(response_text, self.context.conversation_id, tools_used)
            
            duration = time.time() - start_time
            print(f"⏱️  Query processed in {duration:.2f}s")
            
            return response_text

        except Exception as e:
            self.logger.log_error(e, "process_query", self.context.conversation_id)
            error_response = f"❌ Error processing query: {str(e)}"
            self.context.add_assistant_message(error_response)
            return error_response

    async def list_servers_and_tools(self):
        """List all connected servers and their tools"""
        print("\n=== Connected Servers and Tools ===")
        for server_name in self.sessions.keys():
            server_tools = [tool for tool in self.available_tools if tool["_server"] == server_name]
            print(f"\n🖥️  {server_name}:")
            for tool in server_tools:
                print(f"   🔧 {tool['_original_name']}: {tool['description'].replace(f'[{server_name}] ', '')}")
    
    def handle_context_commands(self, command: str) -> str:
        """Maneja comandos relacionados con el contexto"""
        parts = command.split()
        
        if len(parts) == 1:  # Solo 'context'
            return self.context.get_summary()
        
        subcommand = parts[1].lower()
        
        if subcommand == "clear":
            old_id = self.context.conversation_id
            self.context.clear()
            return f"✅ Conversación limpiada. Nueva conversación: {self.context.conversation_id}"
        
        elif subcommand == "show":
            lines = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 5
            messages_to_show = self.context.messages[-lines*2:] if len(self.context.messages) > lines*2 else self.context.messages
            
            if not messages_to_show:
                return "No hay mensajes en el contexto actual"
            
            result = f"=== Últimos {len(messages_to_show)} mensajes ===\n"
            for msg in messages_to_show:
                timestamp = msg["timestamp"][:19]  # Solo YYYY-MM-DD HH:MM:SS
                role_icon = "👤" if msg["role"] == "user" else "🤖"
                content = msg["content"][:100] + "..." if len(msg["content"]) > 100 else msg["content"]
                result += f"[{timestamp}] {role_icon} {content}\n"
            
            return result
        
        else:
            return """
Comandos de contexto disponibles:
• context - Ver resumen de conversación actual  
• context clear - Limpiar conversación y empezar nueva
• context show <n> - Mostrar últimos N intercambios (default: 5)
"""
    
    def handle_log_commands(self, command: str) -> str:
        """Maneja comandos relacionados con logs"""
        parts = command.split()
        
        if len(parts) == 1:  # Solo 'logs'
            return self.logger.get_recent_logs(20)
        
        subcommand = parts[1].lower()
        
        if subcommand == "recent":
            lines = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 50
            return self.logger.get_recent_logs(lines)
        
        elif subcommand == "file":
            return f"📄 Log file location: {self.logger.log_file.absolute()}"
        
        else:
            return """
Comandos de logs disponibles:
• logs - Ver logs recientes (20 líneas)
• logs recent <n> - Ver últimas N líneas de logs
• logs file - Mostrar ubicación del archivo de log
"""
    
    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\n=== 🚀 MCP Multi-Client Started! ===")
        print("Commands:")
        print("  - Type your queries (context is maintained across the conversation)")
        print("  - 'list' to see available servers and tools")
        print("  - 'context ...' for context management")
        print("  - 'logs ...' for log management")
        print("  - 'quit' to exit")
        print(f"\n💬 Conversation ID: {self.context.conversation_id}")
        print(f"📄 Logs are saved to: {self.logger.log_file.absolute()}")

        while True:
            try:
                query = input(f"\n[{self.context.conversation_id}] 🗣️  Query: ").strip()

                if query.lower() == 'quit':
                    break
                elif query.lower() == 'list':
                    await self.list_servers_and_tools()
                    continue
                elif query.lower().startswith('context'):
                    response = self.handle_context_commands(query)
                    print("\n" + response)
                    continue
                elif query.lower().startswith('logs'):
                    response = self.handle_log_commands(query)
                    print("\n" + response)
                    continue
                elif not query:
                    continue

                print("\n🤖 Processing...")
                response = await self.process_query(query)
                print(f"\n🤖 Response:\n{response}")

            except KeyboardInterrupt:
                print("\n\n⚠️  Interrupción detectada...")
                break
            except Exception as e:
                self.logger.log_error(e, "chat_loop", self.context.conversation_id)
                print(f"\n❌ Error: {str(e)}")
        
        print(f"\n👋 Goodbye! All interactions have been logged to: {self.logger.log_file.absolute()}")

    async def cleanup(self):
        """Clean up resources"""
        self.logger.log_shutdown()
        await self.exit_stack.aclose()

async def main():
    client = MCPMultiClient()
    
    try:
        if len(sys.argv) < 2:
            print("Usage:")
            print("  python client.py <config_file>     # Use configuration file")
            print("  python client.py <server_script>   # Single server mode (backward compatibility)")
            return
        
        arg = sys.argv[1]
        
        # Check if argument is a config file or single server script
        if arg.endswith(('.json', '.toml', '.tml')):
            await client.connect_to_servers(arg)
        else:
            # Backward compatibility - single server mode
            await client.connect_to_single_server(arg)
        
        await client.chat_loop()
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())