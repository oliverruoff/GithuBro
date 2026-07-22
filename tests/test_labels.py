from app.github.labels import ensure_workflow_labels, names, transition


class Client:
    def __init__(self, labels=()):
        self.args = None
        self.commands = []
        self.labels = set(labels)

    def command(self, args):
        self.args = args
        self.commands.append(args)
        if args[:2] == ["label", "create"]:
            self.labels.add(args[2])

    def json(self, args):
        assert args[:2] == ["label", "list"]
        return [{"name": name} for name in sorted(self.labels)]


def test_label_names_accept_api_and_plain_shapes():
    assert names([{"name": "agent"}, "bug"]) == {"agent", "bug"}


def test_transition_is_single_issue_edit_call():
    client = Client()
    transition(client, "o/r", 3, add="agent-in-progress", remove="agent")
    assert client.args == [
        "issue", "edit", "3", "--repo", "o/r", "--add-label", "agent-in-progress",
        "--remove-label", "agent",
    ]


def test_ensure_workflow_labels_creates_only_missing_labels():
    client = Client(labels={"agent", "unrelated"})
    created = ensure_workflow_labels(
        client, ("o/r",), trigger="agent",
        in_progress="agent-in-progress", done="agent-done",
    )
    assert created == {"o/r": ("agent-in-progress", "agent-done")}
    assert [command[2] for command in client.commands] == ["agent-in-progress", "agent-done"]
    assert client.commands[0] == [
        "label", "create", "agent-in-progress", "--repo", "o/r",
        "--color", "D4C5F9", "--description", "githubro is processing this issue",
    ]


def test_ensure_workflow_labels_is_idempotent():
    client = Client(labels={"queue", "working", "finished"})
    created = ensure_workflow_labels(
        client, ("o/r",), trigger="queue", in_progress="working", done="finished",
    )
    assert created == {"o/r": ()}
    assert client.commands == []
