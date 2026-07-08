from typing import Any

from langgraph.graph import StateGraph, END
from app.pipeline.state import PrismState   
from app.pipeline.nodes import plan_node, search_node, reflect_node, should_continue, generate_report_node

def build_graph(checkpointer: Any | None = None):
    # 构建状态图
    graph_builder = StateGraph(PrismState)

    # 添加节点
    graph_builder.add_node("plan", plan_node)
    graph_builder.add_node("search", search_node)
    graph_builder.add_node("reflect", reflect_node)
    graph_builder.set_entry_point("plan")
    graph_builder.add_edge('plan', "search")
    graph_builder.add_edge("search", "reflect")
    graph_builder.add_conditional_edges("reflect", should_continue, {
        "continue": "search", # 如果函数返回True，则继续搜索
        "stop": "generate_report" # 如果函数返回False，则停止搜索
    })
    graph_builder.add_node("generate_report", generate_report_node)
    graph_builder.add_edge("generate_report", END)
    # 编译图,把checkpoint传进去,每执行一步都会保存一次状态
    return graph_builder.compile(checkpointer=checkpointer)
