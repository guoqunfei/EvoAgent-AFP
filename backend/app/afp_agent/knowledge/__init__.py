"""AFPAgent 知识库模块 - 抗冻蛋白的文献知识、冰结合基序模式、序列分析"""

from .knowledge_base import AFPKnowledgeBase
from .motifs import AFPMotifLibrary, IceBindingMotif
from .literature import AFPLiteratureKnowledge

__all__ = [
    "AFPKnowledgeBase",
    "AFPMotifLibrary", "IceBindingMotif",
    "AFPLiteratureKnowledge",
]
