# simulator/__init__.py
"""
AFP 模拟器模块
包含：几何评分引擎、物理化学评分器、AFP预测器
"""

from .geometry_scorer import IceBindingGeometryScorer, GeometryScore, IcePlane, ICE_LATTICE
from .physicochemical_scorer import PhysicochemicalScorer
from .afp_predictor import SimpleAFPPredictor
from .simulator import AFPSimulator
