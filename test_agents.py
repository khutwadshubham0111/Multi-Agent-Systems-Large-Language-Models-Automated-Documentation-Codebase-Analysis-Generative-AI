import unittest
import asyncio
import agents


class AgentFallbackTest(unittest.IsolatedAsyncioTestCase):
    async def test_agent_app_without_api_key_still_runs(self):
        sample_doc = (
            "# Test Documentation\n\n"
            "This is a test documentation text for agent verification."
        )
        result = await agents.agent_app(sample_doc)
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)


if __name__ == "__main__":
    unittest.main()
