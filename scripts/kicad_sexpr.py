"""Small KiCad S-expression reader/writer used by reproducible board generation."""
import json
import re


class Atom(str):
    pass


def loads(text):
    tokens = re.findall(r'"(?:\\.|[^"\\])*"|[()]|[^\s()]+', text)
    stack = []
    root = None
    for token in tokens:
        if token == "(":
            node = []
            if stack:
                stack[-1].append(node)
            else:
                if root is not None:
                    raise ValueError("More than one root form")
                root = node
            stack.append(node)
        elif token == ")":
            if not stack:
                raise ValueError("Unmatched closing parenthesis")
            stack.pop()
        else:
            if not stack:
                raise ValueError("Atom outside root")
            stack[-1].append(json.loads(token) if token.startswith('"') else Atom(token))
    if stack or root is None:
        raise ValueError("Unbalanced or empty S-expression")
    return root


def dumps(node):
    if isinstance(node, list):
        return "(" + " ".join(dumps(value) for value in node) + ")"
    if isinstance(node, Atom):
        return str(node)
    if isinstance(node, str):
        return json.dumps(node, ensure_ascii=False)
    return str(node)


def children(node, key):
    return [value for value in node[1:] if isinstance(value, list) and value and value[0] == key]


def child(node, key):
    values = children(node, key)
    return values[0] if values else None


def form(key, *values):
    return [Atom(key), *values]


def symbol_pins(symbol):
    result = {}
    for unit in children(symbol, "symbol"):
        for pin in children(unit, "pin"):
            result[str(child(pin, "number")[1])] = {
                "name": str(child(pin, "name")[1]), "type": str(pin[1]),
                "at": [float(v) for v in child(pin, "at")[1:]],
            }
    return result
