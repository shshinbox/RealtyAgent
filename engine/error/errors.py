from ..graph.schema import NodeType


class WorkflowError(Exception):
    pass


class NodeError(WorkflowError):
    def __init__(
        self,
        message: str,
        code: str = "AGENT_EXECUTION_ERROR",
        node_name: str = "Unknown",
        context: dict | None = None,
    ):
        self.message = message
        self.code = code
        self.node_name = node_name
        self.context = context or {}
        super().__init__(f"[{node_name}] {message}")

    def to_dict(self):
        return {
            "error_type": self.__class__.__name__,
            "code": self.code,
            "message": self.message,
            "node_name": self.node_name,
            "context": self.context,
        }

    def __str__(self):
        return f"[{self.code}] @Node({self.node_name}): {self.message}"


class SecurityError(NodeError):
    def __init__(self, node_name: NodeType, context: dict):
        super().__init__(
            code="SECURED_EXECUTION_ERROR",
            context=context,
            message="Security threat detected.",
            node_name=node_name,
        )
