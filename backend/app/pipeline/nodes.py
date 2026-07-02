from app.pipeline.state import PlaygroundState

# 第一步节点：生成搜索关键词
def plan_node(state: PlaygroundState) -> dict:
    event_query = state['event_query'] #获取用户输入的事件查询
    #TODO: 先不对接llm，直接拼几个固定的关键词
    queries = [f"{event_query} 支持",f"{event_query} 反对"]
    return {"search_queries": queries}

# 第二步节点：根据关键词，模拟搜索结果
def search_node(state: PlaygroundState) -> dict:
    # # 模拟出错抛出异常
    # global _has_crashed_error
    # if not _has_crashed_error:
    #     _has_crashed_error = True
    #     print('搜索节点出错')
    #     raise Exception('模拟出错')


    queries = state['search_queries'] #获取search节点生成的搜索关键词
    # 当前搜索的第几轮
    round_num=state['retry_count'] +1
    #TODO: 先不对接llm，直接拼几个固定的结果
    results = [f"第{round_num}轮搜索结果{i}：{query}" for i, query in enumerate(queries)]
    return {"raw_results": state['raw_results'] + results}

# 第三步节点：根据搜索结果，生成反思结果
def reflect_node(state: PlaygroundState) -> dict:
    print('我进来了')
    # 占位逻辑
    new_count = state['retry_count'] + 1
    return {"retry_count": new_count}

# 第四步节点：根据搜索结果，判断是否需要重试
def should_continue(state: PlaygroundState) -> str:
    print(state['retry_count'], '---> retry_count')
    should_continue = state['retry_count'] < 2
    # 如果搜索结果为空，则重试
    if should_continue:
        print('我继续')
        return 'continue'
    print('我停止')
    return 'stop'
