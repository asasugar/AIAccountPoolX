""" 平台引擎注册 """
from .platforms.openai.engine import OpenAIEngine
from .platforms.registry import registry

openai_engine = OpenAIEngine()
registry.register(openai_engine)
