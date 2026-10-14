import re
from graphql.language import Lexer, Source, TokenKind


def rewrite_quoted_names(src: str):
    """
    Rewrites quoted model identifiers in GraphQL queries/mutations to safe GraphQL identifiers.
    For example:
        "sale.order"(first: 10) -> sale__order(first: 10)
        "res.partner.create"(values: {...}) -> res__partner__create(values: {...})
    Preserves quoted string literals inside argument parentheses (like domains or values).
    Returns (rewritten_query_string, mapping_dict).
    """
    if not src or ('"' not in src and "'" not in src):
        return src, {}

    try:
        lexer = Lexer(Source(src))
        depth = 0
        out = []
        last = 0
        mapping = {}
        tok = lexer.advance()

        while tok.kind != TokenKind.EOF:
            if tok.kind == TokenKind.PAREN_L:
                depth += 1
            elif tok.kind == TokenKind.PAREN_R:
                if depth > 0:
                    depth -= 1
            elif tok.kind == TokenKind.STRING and depth == 0:
                val = tok.value
                # If it looks like a model name (e.g. "res.partner", "sale.order.create", "res.partner")
                if '.' in val or val.isidentifier():
                    safe = val.replace('.', '__')
                    out.append(src[last:tok.start])
                    out.append(safe)
                    last = tok.end
                    mapping[safe] = val
            tok = lexer.advance()

        out.append(src[last:])
        return ''.join(out), mapping
    except Exception:
        # Fallback to regex-based rewriter if lexer fails on unclosed syntax
        return _regex_fallback_rewrite(src)


def _regex_fallback_rewrite(src: str):
    mapping = {}

    def replace_match(m):
        raw = m.group(1)
        safe = raw.replace('.', '__')
        mapping[safe] = raw
        return safe

    pattern = r'"([a-zA-Z_][a-zA-Z0-9_\.]*)"\s*(?=[({:\s])'
    rewritten = re.sub(pattern, replace_match, src)
    return rewritten, mapping


def restore_names(obj, mapping: dict):
    """
    Recursively restores rewritten identifiers in data dictionaries and error paths
    back to their original quoted Odoo model names.
    """
    if not mapping:
        return obj

    if isinstance(obj, dict):
        new_dict = {}
        for k, v in obj.items():
            orig_k = mapping.get(k, k)
            new_dict[orig_k] = restore_names(v, mapping)
        return new_dict
    elif isinstance(obj, list):
        return [restore_names(item, mapping) for item in obj]
    return obj
