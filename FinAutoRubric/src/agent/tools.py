"""Tool implementations confined to one evidence directory."""
import ast
import operator
from pathlib import Path

TEXT_SUFFIXES = {".md", ".txt", ".csv", ".json"}
MAX_CHARS = 4000
MAX_HITS = 20

_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


class ToolError(RuntimeError):
    pass


def safe_eval(expression):
    """Evaluate arithmetic only: no names, calls or attribute access."""
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ToolError("cannot parse expression: %s" % exc)

    def walk(node):
        if isinstance(node, ast.Expression):
            return walk(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _OPERATORS:
            return _OPERATORS[type(node.op)](walk(node.left), walk(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in _OPERATORS:
            return _OPERATORS[type(node.op)](walk(node.operand))
        raise ToolError("disallowed expression element: %s" % type(node).__name__)

    return walk(tree)


class Toolbox:
    """Read/search/calculate over one question's evidence directory."""

    def __init__(self, evidence_dir):
        self.root = Path(evidence_dir).resolve()

    def specs(self):
        return [
            {
                "type": "function",
                "function": {
                    "name": "read_evidence",
                    "description": "Read a text file under the evidence directory.",
                    "parameters": {
                        "type": "object",
                        "properties": {"path": {"type": "string"}},
                        "required": ["path"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "search_evidence",
                    "description": "Case-insensitive substring search over evidence files.",
                    "parameters": {
                        "type": "object",
                        "properties": {"query": {"type": "string"}},
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "calculate",
                    "description": "Evaluate an arithmetic expression (numbers and + - * / % ** only).",
                    "parameters": {
                        "type": "object",
                        "properties": {"expression": {"type": "string"}},
                        "required": ["expression"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "submit",
                    "description": "Submit the final answer and end the episode.",
                    "parameters": {
                        "type": "object",
                        "properties": {"answer": {"type": "string"}},
                        "required": ["answer"],
                    },
                },
            },
        ]

    def resolve(self, relative):
        target = (self.root / relative).resolve()
        if target != self.root and self.root not in target.parents:
            raise ToolError("path escapes evidence directory: %s" % relative)
        return target

    def call(self, name, args):
        handler = {
            "read_evidence": self.read_evidence,
            "search_evidence": self.search_evidence,
            "calculate": self.calculate,
            "submit": self.submit,
        }.get(name)
        if handler is None:
            raise ToolError("unknown tool: %s" % name)
        return handler(**args)

    def read_evidence(self, path):
        target = self.resolve(path)
        if not target.is_file():
            raise ToolError("no such evidence file: %s" % path)
        text = target.read_text(encoding="utf-8-sig", errors="replace")
        return {"path": path, "chars": len(text), "truncated": len(text) > MAX_CHARS, "text": text[:MAX_CHARS]}

    def search_evidence(self, query):
        if not query.strip():
            raise ToolError("empty query")
        needle = query.lower()
        hits = []
        for path in sorted(self.root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            for number, line in enumerate(path.read_text(encoding="utf-8-sig", errors="replace").splitlines(), start=1):
                if needle in line.lower():
                    hits.append({"file": path.relative_to(self.root).as_posix(), "line": number, "text": line.strip()[:300]})
                    if len(hits) >= MAX_HITS:
                        return {"query": query, "hits": hits, "truncated": True}
        return {"query": query, "hits": hits, "truncated": False}

    def calculate(self, expression):
        return {"expression": expression, "value": safe_eval(expression)}

    def submit(self, answer):
        if not str(answer).strip():
            raise ToolError("empty final answer")
        return {"accepted": True, "answer_chars": len(str(answer))}
