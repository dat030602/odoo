import difflib
import json


def dump_json(data):
    """Pretty-print JSON with 2-space indentation and sorted keys."""
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False, default=str)


def norm(v):
    """Normalize empty representations (False, None, '') to None, and strip strings."""
    if v in (False, None, ''):
        return None
    if isinstance(v, str):
        s = v.strip()
        return s if s else None
    return v


def same(old, new, keys):
    """Compare two dictionaries on specific keys with normalization."""
    return all(norm(old.get(k)) == norm(new.get(k)) for k in keys)


def count_diff(old, new):
    """Count added and removed lines between two text blocks."""
    old_lines = (old or '').splitlines()
    new_lines = (new or '').splitlines()
    sm = difflib.SequenceMatcher(None, old_lines, new_lines, autojunk=False)
    added = 0
    removed = 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag in ('replace', 'delete'):
            removed += i2 - i1
        if tag in ('replace', 'insert'):
            added += j2 - j1
    return added, removed


def dump_server_action(v):
    """Standardized representation for server action comparison."""
    head = [
        'name: %s' % (v.get('name') or ''),
        'state: %s' % (v.get('state') or ''),
        'model: %s' % (v.get('model') or ''),
        'binding_model: %s' % (v.get('binding_model') or ''),
        'binding_type: %s' % (v.get('binding_type') or ''),
    ]
    return '\n'.join(head + ['--- code ---', v.get('code') or ''])
