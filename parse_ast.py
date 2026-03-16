import ast

class CallGraphVisitor(ast.NodeVisitor):
    def __init__(self):
        self.current_func = None
        self.calls = {}

    def visit_FunctionDef(self, node):
        self.current_func = node.name
        self.calls[node.name] = []
        self.generic_visit(node)
        self.current_func = None

    def visit_Call(self, node):
        if self.current_func:
            if isinstance(node.func, ast.Name):
                self.calls[self.current_func].append(node.func.id)
        self.generic_visit(node)

with open('scripts/download_uup.py', 'r') as f:
    tree = ast.parse(f.read())

visitor = CallGraphVisitor()
visitor.visit(tree)

for func, calls in visitor.calls.items():
    print(f"{func} calls: {set(calls)}")
