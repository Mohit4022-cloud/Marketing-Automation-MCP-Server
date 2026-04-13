"""Marketing Automation MCP Server implementation."""

import asyncio
import logging
from typing import Any, Dict, List
import json

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .models import (
    AnalyzeAudienceSegmentsInput,
    CreateCampaignCopyInput,
    GenerateCampaignReportInput,
    OptimizeCampaignBudgetInput,
)
from .tools.marketing_tools import (
    generate_campaign_report,
    optimize_campaign_budget,
    create_campaign_copy,
    analyze_audience_segments
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MarketingAutomationServer:
    def __init__(self):
        self.server = Server("marketing-automation")
        self._setup_handlers()
        
    def _setup_handlers(self):
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """List all available marketing automation tools"""
            return [
                Tool(
                    name="generate_campaign_report",
                    description="Generate campaign performance reports using live platform data or explicit demo mode.",
                    inputSchema=GenerateCampaignReportInput.model_json_schema(),
                ),
                Tool(
                    name="optimize_campaign_budget",
                    description="Reallocate campaign budget using live platform metrics and provider-backed optimization logic.",
                    inputSchema=OptimizeCampaignBudgetInput.model_json_schema(),
                ),
                Tool(
                    name="create_campaign_copy",
                    description="Generate campaign copy variants through the configured AI provider or deterministic demo mode.",
                    inputSchema=CreateCampaignCopyInput.model_json_schema(),
                ),
                Tool(
                    name="analyze_audience_segments",
                    description="Analyze audience segments in deterministic demo mode or return a structured live-mode block.",
                    inputSchema=AnalyzeAudienceSegmentsInput.model_json_schema(),
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Execute a marketing automation tool"""
            try:
                if name == "generate_campaign_report":
                    # Validate input
                    input_data = GenerateCampaignReportInput(**arguments)
                    result = await generate_campaign_report(input_data)
                    
                elif name == "optimize_campaign_budget":
                    # Validate input
                    input_data = OptimizeCampaignBudgetInput(**arguments)
                    result = await optimize_campaign_budget(input_data)
                    
                elif name == "create_campaign_copy":
                    # Validate input
                    input_data = CreateCampaignCopyInput(**arguments)
                    result = await create_campaign_copy(input_data)
                    
                elif name == "analyze_audience_segments":
                    # Validate input
                    input_data = AnalyzeAudienceSegmentsInput(**arguments)
                    result = await analyze_audience_segments(input_data)
                    
                else:
                    result = {"error": f"Unknown tool: {name}"}
                
                # Convert result to JSON string for MCP response
                result_str = json.dumps(
                    result.model_dump(mode="json") if hasattr(result, "model_dump") else result,
                    default=str,
                    indent=2,
                )
                return [TextContent(type="text", text=result_str)]
                
            except Exception as e:
                logger.error(f"Error executing tool {name}: {e}")
                error_response = {"error": str(e), "tool": name}
                return [TextContent(type="text", text=json.dumps(error_response, indent=2))]
    
    async def run(self):
        """Run the MCP server"""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="marketing-automation",
                    server_version="1.0.0"
                )
            )


async def main():
    """Main entry point"""
    server = MarketingAutomationServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
