# 导入json
import asyncio
import json
from functools import lru_cache

# 导入langchain_openai
from langchain_openai import ChatOpenAI

# 导入tavily
from tavily import TavilyClient

# 导入配置
from app.core.config import settings
from app.core.debug_log import debug_panel

# 导入反思节点
from app.pipeline.state import PrismState


@lru_cache(maxsize=1)
def get_llm() -> ChatOpenAI:
    if not settings.OPENAI_API_KEY:
        raise RuntimeError(
            "OPENAI_API_KEY 未配置，请在 backend/.env 中填写 DeepSeek API key"
        )

    # DeepSeek 提供 OpenAI-compatible API，langchain_openai 可以通过 base_url 直连
    # temperature=0 表示输出尽量稳定，不需要随机发挥-需要结构化输出的场景很重要
    return ChatOpenAI(
        model=settings.OPENAI_MODEL,
        temperature=0,
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL,
    )


# 初始化tavily搜索客户端
tavily_client = TavilyClient(api_key=settings.TAVILY_API_KEY)


# 第一步节点：生成搜索关键词
async def plan_node(state: PrismState) -> dict:
    event_query = state["event_query"]  # 获取用户输入的事件查询
    # 用ainvoke 异步调用llm，生成搜索关键词
    # 生成4个不同立场的搜索关键词
    prompt = (
        prompt
    ) = f"""你是一个专业的媒体分析助手。用户想了解以下事件的多方报道：{event_query}

请生成4个搜索关键词，要求：
1. 每个关键词要像真实用户在搜索引擎里搜索的样子，简洁直接
2. 分别覆盖不同角度：支持方、反对方、中立事实、国际视角
3. 关键词里要包含事件的核心名词，不要出现"正面报道"、"支持观点"这类元描述词

举例：如果事件是"某城市垃圾分类新政策"，好的关键词是：
["垃圾分类政策 市民支持", "垃圾分类强制执行 争议", "垃圾分类实施效果", "China waste sorting policy"]

只返回JSON数组，不要有任何其他文字：
["关键词1", "关键词2", "关键词3", "关键词4"]"""
    response = await get_llm().ainvoke(prompt)

    # response.content 是llm返回的字符串，需要解析成python列表
    try:
        queries = json.loads(response.content)
    except json.JSONDecodeError:
        # 如果llm没有按json格式返回，降级到占位逻辑
        queries = [
            f"{event_query} 支持",
            f"{event_query} 反对",
            f"{event_query} 报道",
            f"{event_query} international",
        ]

    debug_panel(
        "pipeline",
        "plan_node generated search queries",
        {"event_query": event_query, "queries": queries},
    )
    return {"search_queries": queries}


# 第二步节点：根据关键词，用tavily真正去搜索，累积搜索结果
async def search_node(state: PrismState) -> dict:
    queries = state["search_queries"]  # 获取search节点生成的搜索关键词
    new_results = []
    for query in queries:
        try:
            # tavily search方法：max_results控制每个关键词返回几条结果
            # 因tavily.search是同步的，所以需要用asyncio.to_thread包装一下
            # include_raw_content=false 表示只要摘要，不要正文（省token）
            results = await asyncio.to_thread(
                tavily_client.search,
                query,
                max_results=3,
                include_raw_content=False,
            )
            # results["results"] 是列表，每个元素是一个字典，包含title, url, content
            for r in results.get("results", []):
                new_results.append(
                    {
                        "query": query,
                        "title": r["title"],
                        "url": r["url"],
                        "content": r["content"],
                    }
                )
        except Exception as e:
            debug_panel(
                "pipeline",
                "search_node query failed",
                {"query": query, "error": str(e)},
                status="error",
            )

    debug_panel(
        "pipeline",
        "search_node collected results",
        {
            "query_count": len(queries),
            "new_result_count": len(new_results),
            "total_result_count": len(state["raw_results"]) + len(new_results),
            "sample_titles": [result["title"] for result in new_results[:5]],
        },
    )
    return {"raw_results": state["raw_results"] + new_results}


# 第三步节点：根据搜索结果，生成反思结果
async def reflect_node(state: PrismState) -> dict:
    debug_panel(
        "pipeline",
        "reflect_node evaluating coverage",
        {
            "raw_result_count": len(state["raw_results"]),
            "retry_count": state["retry_count"],
        },
    )
    # 获取搜索结果
    raw_results = state["raw_results"]
    # 获取重试次数
    retry_count = state["retry_count"]

    # 把搜索结果整理成文字，让llm进行评估
    results_text = "\n".join(
        [f"- [{r['title']}]({r['url']})：{r['content'][:200]}" for r in raw_results]
    )
    response = await get_llm().ainvoke(
        f"""你是一个媒体分析助手，正在评估以下搜索结果是否覆盖了足够多样的立场：

    {results_text}

    原始事件：{state['event_query']}

    请判断：这些搜索结果是否已经包含了支持、反对、中立、国际视角(如有，非必要)这几个不同立场的报道？如果不足，请补充哪些视角？

    只返回JSON，格式如下，不要有任何其他文字：
    {{"is_sufficient": true或false, "missing_perspectives": ["缺少的视角1", "缺少的视角2"]}}"""
    )
    try:
        # 如果llm按json格式返回，解析成python字典
        result = json.loads(response.content)
        # 获取llm的判断结果 false表示不足，true表示足够
        is_sufficient = result.get("is_sufficient", False)
        # 获取llm补充的视角
        missing = result.get("missing_perspectives", [])
    except json.JSONDecodeError:
        # 解析失败，保守默认为覆盖不够，再来一轮
        is_sufficient = False
        missing = []
    # 如果覆盖不够，则需要重试
    new_queries = state["search_queries"]
    if not is_sufficient and missing:
        new_queries = [q for q in new_queries if q not in missing]
        debug_panel(
            "pipeline",
            "reflect_node missing perspectives",
            {"missing_perspectives": missing, "next_queries": new_queries},
            status="warning",
        )
    else:
        debug_panel(
            "pipeline",
            "reflect_node coverage result",
            {"is_sufficient": is_sufficient, "missing_perspectives": missing},
            status="success" if is_sufficient else "warning",
        )
    return {
        "retry_count": retry_count + 1,
        "search_queries": new_queries,
    }


# 第四步节点：根据搜索结果，判断是否需要重试
def should_continue(state: PrismState) -> str:
    should_continue = state["retry_count"] < 2
    # 如果搜索结果为空，则重试
    if should_continue:
        debug_panel(
            "pipeline",
            "route decision",
            {"retry_count": state["retry_count"], "next": "continue"},
            status="warning",
        )
        return "continue"
    debug_panel(
        "pipeline",
        "route decision",
        {"retry_count": state["retry_count"], "next": "stop"},
        status="success",
    )
    return "stop"

# 步骤5: 生成最终报告
async def generate_report_node(state: PrismState) -> dict:
    raw_results = state["raw_results"]
    event_query = state["event_query"]

    # 把所有搜索结果整理成文字，让llm生成最终报告
    results_text = "\n".join([
        f"- 来源：{r['title']}（{r['url']}）\n  内容：{r['content'][:300]}"
        for r in raw_results
    ])
    results_text = "\n".join([
        f"- 来源：{r['title']}（{r['url']}）\n  内容：{r['content'][:300]}"
        for r in raw_results
    ])

    response = await get_llm().ainvoke(
        f"""你是一个专业的媒体分析助手，请分析以下关于「{event_query}」的多方报道。

        搜索结果：
        {results_text}

        请整合出一份结构化的分析报告，包含以下三个部分：
        1. 共识：所有来源都认可的基本事实
        2. 分歧：不同来源之间存在明显差异的观点或叙述角度
        3. 沉默：所有来源都没有提到、但可能值得关注的角度（如果能识别出来的话）

        只返回JSON，格式如下，不要有任何其他文字：
        {{
          "consensus": ["共识点1", "共识点2"],
          "divergence": [
            {{
              "topic": "分歧点描述",
              "perspectives": ["角度1", "角度2"]
            }}
          ],
          "silence": ["沉默点1", "沉默点2"]
        }}"""
    )
    try:
        report = json.loads(response.content)
    except json.JSONDecodeError:
        # 如果llm没有按json格式返回，降级到占位逻辑
        return {"report": {"consensus": [], "divergence": [], "silence": [], "raw_results": response.content}}

    debug_panel(
        "pipeline",
        "generate_report_node result",
        {"report": report},
        status="success",
    )
    return {"final_report": report}
