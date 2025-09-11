# MCP 

## Create a new directory for our project
```comandline
uv init taylor
cd taylor
```

## Create virtual environment and activate it
```comandline
uv venv
source .venv/bin/activate
```

## Install dependencies
```comandline
uv add "mcp[cli]" httpx
```
