import unittest

from agent_system import route_to_agent, validate_user_request


class TestRouting(unittest.TestCase):
    def test_route_defaults_to_planner(self):
        self.assertEqual(route_to_agent({"selected_agent": None}), "planner")

    def test_route_planner(self):
        self.assertEqual(route_to_agent({"selected_agent": "planner"}), "planner")

    def test_route_coach(self):
        self.assertEqual(route_to_agent({"selected_agent": "coach"}), "coach")

    def test_route_analysis(self):
        self.assertEqual(route_to_agent({"selected_agent": "analysis"}), "analysis")


class TestValidation(unittest.TestCase):
    def test_empty_request(self):
        message = validate_user_request("")
        self.assertIsNotNone(message)

    def test_non_empty_request(self):
        message = validate_user_request("테스트 요청")
        self.assertIsNone(message)


if __name__ == "__main__":
    unittest.main()
