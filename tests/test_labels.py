from app.github.labels import names, transition


class Client:
    def __init__(self): self.args = None
    def command(self, args): self.args = args


def test_label_names_accept_api_and_plain_shapes():
    assert names([{"name": "agent"}, "bug"]) == {"agent", "bug"}


def test_transition_is_single_issue_edit_call():
    client = Client()
    transition(client, "o/r", 3, add="agent-in-progress", remove="agent")
    assert client.args == [
        "issue", "edit", "3", "--repo", "o/r", "--add-label", "agent-in-progress",
        "--remove-label", "agent",
    ]
