import copy
import re
from collections import namedtuple
from lxml import etree

PARSER = etree.XMLParser(remove_comments=True, resolve_entities=False, no_network=True)
MergeResult = namedtuple('MergeResult', 'new_arch old_view_text added present wrapped error')


def _err(msg):
    return MergeResult('', '', [], [], False, msg)


def serialize(elements):
    return [etree.tostring(e, encoding='unicode', with_tail=False).strip() for e in elements]


def _parse(arch):
    return etree.fromstring((arch or '').encode('utf-8'), PARSER)


def _canon(el):
    node = copy.deepcopy(el)
    node.tail = None
    for n in node.iter():
        if n.text is not None:
            n.text = n.text.strip() or None
        if n.tail is not None:
            n.tail = n.tail.strip() or None
    return etree.tostring(node, method='c14n')


def canonical_text(arch):
    """Normalize XML string to canonical format, stripping comments and formatting differences."""
    if not arch:
        return ''
    try:
        return _canon(_parse(arch)).decode('utf-8')
    except Exception:
        return (arch or '').strip()


def _indent(text, n):
    pad = ' ' * n
    return '\n'.join(pad + line if line.strip() else line for line in text.splitlines())


def _splice(text, frag):
    if re.search(r'<data\s*/>\s*$', text.strip()):
        return re.sub(r'<data\s*/>\s*$', '<data>\n' + frag + '\n</data>', text.strip())
    idx = text.rfind('</data>')
    if idx != -1:
        return text[:idx].rstrip() + '\n' + frag + '\n' + text[idx:]
    # If no closing tag found, wrap both in data
    return '<data>\n' + _indent(text, 4) + '\n' + frag + '\n</data>'


def plan_append(source_arch, target_arch, source_inherit, target_inherit):
    """
    Append child elements of source view into target view's <data> tag.
    Returns MergeResult(new_arch, old_view_text, added, present, wrapped, error).
    """
    if not target_inherit:
        return _err('Target view is a primary view (no inherit_id); use a Create step instead.')
    if not source_inherit and not (source_arch and '<data' in source_arch):
        return _err('Source view is not an inherited view.')

    try:
        src = _parse(source_arch)
    except Exception as e:
        return _err('Invalid source XML: %s' % e)

    if src.tag == 'data':
        items = [c for c in src if isinstance(c.tag, str)]
    elif source_inherit:
        items = [src]
    else:
        return _err('Source view root element is neither <data> nor an inherited view element.')

    try:
        tgt = _parse(target_arch)
    except Exception as e:
        return _err('Invalid target XML: %s' % e)

    wrapped = (tgt.tag != 'data')
    keys = {_canon(tgt)} if wrapped else {_canon(c) for c in tgt if isinstance(c.tag, str)}
    base = re.sub(r'^\s*<\?xml[^>]*\?>', '', target_arch or '').strip()
    old_text = '<data>\n' + _indent(base, 4) + '\n</data>' if wrapped else base

    added = []
    present = []
    for it in items:
        k = _canon(it)
        if k in keys:
            present.append(it)
        else:
            added.append(it)
            keys.add(k)

    if not added:
        return MergeResult(old_text, old_text, [], present, wrapped, None)

    frag = '\n'.join(_indent(etree.tostring(i, encoding='unicode', with_tail=False).strip(), 4) for i in added)
    new_text = _splice(old_text, frag)

    try:
        _parse(new_text)
    except etree.XMLSyntaxError as e:
        return _err('Merged arch is invalid XML: %s' % e)

    return MergeResult(new_text, old_text, added, present, wrapped, None)
