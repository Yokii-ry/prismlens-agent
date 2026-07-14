import unittest
from unittest.mock import patch

from app.pipeline import nodes


class PipelineNodesTest(unittest.IsolatedAsyncioTestCase):
    async def test_search_node_collects_tavily_results(self) -> None:
        with patch.object(
            nodes.tavily_client,
            "search",
            return_value={
                "results": [
                    {
                        "title": "报道标题",
                        "url": "https://example.com/report",
                        "content": "报道摘要",
                    }
                ]
            },
        ):
            result = await nodes.search_node(
                {
                    "event_query": "政策影响分析",
                    "search_queries": ["政策影响分析"],
                    "raw_results": [],
                    "retry_count": 0,
                    "final_report": {},
                }
            )

        self.assertEqual(
            result,
            {
                "raw_results": [
                    {
                        "query": "政策影响分析",
                        "title": "报道标题",
                        "url": "https://example.com/report",
                        "content": "报道摘要",
                    }
                ]
            },
        )


if __name__ == "__main__":
    unittest.main()
