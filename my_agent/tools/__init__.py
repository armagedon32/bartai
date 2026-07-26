from .registry import ToolRegistry
from .web_search import WebSearchTool, WebFetchTool
from .file_ops import FileOpsTool
from .code_exec import CodeExecTool, InstallPackageTool
from .api_tools import APITool
from .memory_search import MemorySearchTool
from .system_info import SystemInfoTool
from .image_gen import GenerateImageTool
from .chart_gen import CreateChartTool
from .table_gen import CreateTableTool
from .math_tools import ComputeMathTool
from .research import ResearchTool, SummarizeTool
from .writing import WriteDocumentTool, TranslateTool
from .writing_checks import CheckWritingTool, RephraseTool


def register_all(registry: ToolRegistry, memory_index=None):
    registry.register(WebSearchTool())
    registry.register(WebFetchTool())
    registry.register(FileOpsTool())
    registry.register(CodeExecTool())
    registry.register(InstallPackageTool())
    registry.register(APITool())
    registry.register(SystemInfoTool())
    registry.register(GenerateImageTool())
    registry.register(CreateChartTool())
    registry.register(CreateTableTool())
    registry.register(ComputeMathTool())
    registry.register(ResearchTool())
    registry.register(SummarizeTool())
    registry.register(WriteDocumentTool())
    registry.register(TranslateTool())
    registry.register(CheckWritingTool())
    registry.register(RephraseTool())
    registry.register(MemorySearchTool(memory_index))
