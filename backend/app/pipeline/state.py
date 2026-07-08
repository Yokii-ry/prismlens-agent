from typing import TypedDict

class PrismState(TypedDict):
    event_query: str  #用户输入的事件查询
    search_queries: list[str] #plan节点生成的搜索关键词
    raw_results: list[dict] #search节点产出的搜索结果
    retry_count: int #重试次数
    final_report: dict #最终报告