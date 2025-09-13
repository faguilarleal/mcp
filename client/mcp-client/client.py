import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from anthropic import Anthropic
from dotenv import load_dotenv

# Try to import tomllib (Python 3.11+) or tomli for older versions
try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

load_dotenv()
MODEL = "claude-sonnet-4-20250514"

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
                print(f"Skipping disabled server: {server_name}")
                continue
                
            try:
                print(f"Connecting to server: {server_name}")
                
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
                for tool in response.tools:
                    tool_info = {
                        "name": f"{tool.name}",  # Prefix with server name
                        "description": f"[{server_name}] {tool.description}",
                        "input_schema": tool.inputSchema,
                        "_server": server_name,
                        "_original_name": tool.name
                    }
                    server_tools.append(tool_info)
                    self.available_tools.append(tool_info)
                
                print(f"✓ Connected to {server_name} with tools: {[tool.name for tool in response.tools]}")
                
            except Exception as e:
                print(f"✗ Failed to connect to {server_name}: {str(e)}")
        
        if not connected_servers:
            raise RuntimeError("No servers could be connected")
        
        print(f"\nSuccessfully connected to {len(connected_servers)} server(s)")
        print(f"Total available tools: {len(self.available_tools)}")
    
    async def connect_to_single_server(self, server_script_path: str):
        """Connect to a single server (backward compatibility)"""
        is_python = server_script_path.endswith('.py')
        is_js = server_script_path.endswith('.js')
        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")

        command = "python" if is_python else "node"
        server_params = StdioServerParameters(
            command=command,
            args=[server_script_path],
            env=None
        )

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        stdio, write = stdio_transport
        session = await self.exit_stack.enter_async_context(ClientSession(stdio, write))
        await session.initialize()
        
        server_name = "default"
        self.sessions[server_name] = session

        # Get tools
        response = await session.list_tools()
        for tool in response.tools:
            self.available_tools.append({
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema,
                "_server": server_name,
                "_original_name": tool.name
            })

        print(f"\nConnected to server with tools: {[tool.name for tool in response.tools]}")


    async def process_query(self, query: str) -> str:
        """Process a query using Claude and available tools"""
        import copy

        messages = [{"role": "user", "content": query}]

        # --- Prepara herramientas para Claude ---
        claude_tools = []
        for tool in self.available_tools:
            # Asegurarse de que el nombre es válido
            valid_name = tool["name"].replace(".", "_")  # ya debería ser así
            claude_tool = {
                "name": valid_name,
                "description": tool["description"],
                "input_schema": tool["input_schema"]
            }
            claude_tools.append(claude_tool)

        # --- Llamada inicial a Claude ---
        response = self.anthropic.messages.create(
            model=MODEL,
            max_tokens=1000,
            messages=messages,
            tools=claude_tools
        )

        final_text = []
        assistant_message_content = []

        # --- Procesa la respuesta de Claude ---
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
                    final_text.append(f"[Error: Tool {tool_name} not found]")
                    continue

                server_name = tool_info["_server"]
                original_tool_name = tool_info["_original_name"]

                # Llamada segura al servidor
                try:
                    session = self.sessions[server_name]
                    result = await session.call_tool(original_tool_name, tool_args)

                    final_text.append(f"[Called {tool_name} on {server_name}]")

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
                        max_tokens=1000,
                        messages=messages,
                        tools=claude_tools
                    )

                    if response.content and response.content[0].text:
                        final_text.append(response.content[0].text)

                except Exception as e:
                    final_text.append(f"[Error calling {tool_name}: {str(e)}]")

        return "\n".join(final_text)



    async def list_servers_and_tools(self):
        """List all connected servers and their tools"""
        print("\n=== Connected Servers ===")
        for server_name in self.sessions.keys():
            server_tools = [tool for tool in self.available_tools if tool["_server"] == server_name]
            print(f"\n{server_name}:")
            for tool in server_tools:
                print(f"  - {tool['_original_name']}: {tool['description'].replace(f'[{server_name}] ', '')}")
    
    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\n=== MCP Multi-Client Started! ===")
        print("Commands:")
        print("  - Type your queries")
        print("  - 'list' to see available servers and tools")
        print("  - 'quit' to exit")

        while True:
            try:
                query = input("\nQuery: ").strip()

                if query.lower() == 'quit':
                    break
                elif query.lower() == 'list':
                    await self.list_servers_and_tools()
                    continue

                response = await self.process_query(query)
                print("\n" + response)

            except Exception as e:
                print(f"\nError: {str(e)}")

    async def cleanup(self):
        """Clean up resources"""
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
        print(f"Error: {str(e)}")
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())