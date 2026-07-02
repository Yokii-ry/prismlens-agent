#ARQ任务队列
# TypedDict：用来定义一个"长得像字典，但有固定字段和类型"的结构
# 这是LangGraph官方推荐的State写法，本质就是一个字典，但有类型提示
from typing import TypedDict
# memorySaver: 用来保存状态的工具
from langgraph.checkpoint.memory import MemorySaver
# StateGraph: 用来构建状态图
from langgraph.graph import StateGraph, END






#=====ARQ Worker=====   

async def run_research_graph(ctx:dict,event_query:str) -> dict:
    print(f"ARQ Worker收到任务: {event_query},开始跑图,任务id: {ctx['job_id']}")
    # 每个任务有一个唯一的thread_id
    #使用ctx的job_id作为thread_id
    config = {'thread_id': ctx['job_id']}
    result = graph.invoke({"event_query": event_query, "retry_count": 0, "raw_results": [], "search_queries": []}, config=config)
    print(f"ARQ Worker完成任务: {event_query},结果: {result}")
    return result

class workerSetting:
    functions = [run_research_graph]    