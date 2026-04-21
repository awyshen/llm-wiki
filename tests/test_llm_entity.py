import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.process.llm_entity_extractor import get_llm_entity_extractor
from src.process.llm_client import get_llm_client

text = open("wiki/articles/llm_wiki.md", "r").read()

llm_entity_extractor = get_llm_entity_extractor()

# build prompt
prompt = llm_entity_extractor._get_entity_extraction_prompt(text)

print("prompt: ", prompt)

result = llm_entity_extractor.llm_client.generate_wiki_page(
    title="实体抽取",
    content=prompt,
    use_batch=False,
    system_prompt="你是一个实体抽取专家，擅长从文本中提取实体信息。",
    task_type="entity_extraction"
)

print(result)