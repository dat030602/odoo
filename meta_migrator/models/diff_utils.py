import difflib
import json
import re
import unicodedata


def slugify_xml_id(text, prefix=None):
    """Normalize and slugify a string to be a valid Odoo XML ID component."""
    if not text:
        text = 'record'
    # Normalize unicode / unaccent Vietnamese characters
    nfkd = unicodedata.normalize('NFKD', str(text))
    ascii_text = nfkd.encode('ASCII', 'ignore').decode('utf-8').lower()
    # Replace non-alphanumeric characters with underscore
    clean = re.sub(r'[^a-z0-9_]+', '_', ascii_text)
    clean = re.sub(r'_+', '_', clean).strip('_')
    if not clean:
        clean = 'record'
    if prefix:
        p = prefix.rstrip('_') + '_'
        if not clean.startswith(p):
            clean = f"{p}{clean}"
    return clean


def build_xml_id(module_name, object_type, name, model_name=None):
    """Generate a standard XML ID: <module_name>.<slugified_name>."""
    mod = (module_name or 'meta_migrator').strip()
    prefix_map = {
        'model': 'model_',
        'field': 'field_',
        'view': 'view_',
        'server_action': 'action_',
        'menu': 'menu_',
        'access_right': 'access_',
        'record_rule': 'rule_',
    }
    p = prefix_map.get(object_type, '')
    if object_type == 'model':
        clean_name = slugify_xml_id(name or model_name, prefix='model_')
    elif object_type == 'field':
        clean_m = slugify_xml_id(model_name).replace('.', '_')
        clean_f = slugify_xml_id(name)
        clean_name = f"field_{clean_m}__{clean_f}"
    elif object_type == 'view' and model_name:
        clean_m = slugify_xml_id(model_name).replace('.', '_')
        clean_n = slugify_xml_id(name)
        if clean_m not in clean_n:
            clean_name = f"view_{clean_m}_{clean_n}"
        else:
            clean_name = slugify_xml_id(name, prefix='view_')
    else:
        clean_name = slugify_xml_id(name, prefix=p)
    return f"{mod}.{clean_name}"


def replace_action_references_in_arch(arch, source_rpc, target_rpc, target_module, cache=None):
    """Scan view arch for source action integer IDs and replace with %(target_xml_id)d."""
    if not arch or not source_rpc:
        return arch

    cache = cache if cache is not None else {}
    target_mod = (target_module or 'meta_migrator').strip()

    # Find candidates from %(id)d pattern
    candidate_ids = set()
    for m in re.finditer(r'%\((\d+)\)d', arch):
        candidate_ids.add(int(m.group(1)))

    # Find candidates from name="id" inside type="action" buttons
    btn_pattern1 = re.compile(r'<button\b[^>]*\btype=["\']action["\'][^>]*\bname=["\'](\d+)["\']')
    btn_pattern2 = re.compile(r'<button\b[^>]*\bname=["\'](\d+)["\'][^>]*\btype=["\']action["\']')
    action_attr_pattern = re.compile(r'\baction=["\'](\d+)["\']')
    for m in btn_pattern1.finditer(arch):
        candidate_ids.add(int(m.group(1)))
    for m in btn_pattern2.finditer(arch):
        candidate_ids.add(int(m.group(1)))
    for m in action_attr_pattern.finditer(arch):
        candidate_ids.add(int(m.group(1)))

    if not candidate_ids:
        return arch

    new_arch = arch
    for act_id in candidate_ids:
        cache_key = ('resolved_act_xml_id', act_id, target_mod)
        if cache_key in cache:
            target_xml_id = cache[cache_key]
        else:
            target_xml_id = False
            # Check ir.actions.server on source
            src_server_acts = source_rpc.read(
                'ir.actions.server', [act_id],
                ['id', 'name', 'model_id', 'state', 'code'],
            )
            if src_server_acts:
                act_name = src_server_acts[0].get('name') or f"server_action_{act_id}"
                # Check if source had an xml_id
                src_data = source_rpc.search_read(
                    'ir.model.data',
                    [('model', '=', 'ir.actions.server'), ('res_id', '=', act_id)],
                    ['module', 'name'], limit=1,
                )
                if src_data and src_data[0].get('name'):
                    target_xml_id = f"{target_mod}.{src_data[0]['name']}"
                else:
                    target_xml_id = build_xml_id(target_mod, 'server_action', act_name)
            else:
                # Check ir.actions.act_window on source
                src_win_acts = source_rpc.read(
                    'ir.actions.act_window', [act_id],
                    ['id', 'name', 'res_model'],
                )
                if src_win_acts:
                    act_name = src_win_acts[0].get('name') or f"window_action_{act_id}"
                    src_data = source_rpc.search_read(
                        'ir.model.data',
                        [('model', '=', 'ir.actions.act_window'), ('res_id', '=', act_id)],
                        ['module', 'name'], limit=1,
                    )
                    if src_data and src_data[0].get('name'):
                        target_xml_id = f"{target_mod}.{src_data[0]['name']}"
                    else:
                        target_xml_id = build_xml_id(target_mod, 'menu', act_name)

            cache[cache_key] = target_xml_id

        if target_xml_id:
            # Replace %(act_id)d -> %(target_xml_id)d
            new_arch = re.sub(
                r'%\(' + str(act_id) + r'\)d',
                f"%({target_xml_id})d",
                new_arch,
            )
            # Replace name="act_id" in type="action" buttons
            new_arch = re.sub(
                r'(<button\b[^>]*\btype=["\']action["\'][^>]*\bname=)["\']' + str(act_id) + r'["\']',
                r'\1"%(' + target_xml_id + r')d"',
                new_arch,
            )
            new_arch = re.sub(
                r'(<button\b[^>]*\bname=)["\']' + str(act_id) + r'["\']([^>]*\btype=["\']action["\'])',
                r'\1"%(' + target_xml_id + r')d"\2',
                new_arch,
            )
            # Replace action="act_id"
            new_arch = re.sub(
                r'(\baction=)["\']' + str(act_id) + r'["\']',
                r'\1"%(' + target_xml_id + r')d"',
                new_arch,
            )

    return new_arch


def sync_action_id_in_target_views(target_rpc, src_action_id, target_xml_id):
    """Search views on target that contain the source action integer ID and replace with %(target_xml_id)d."""
    if not target_rpc or not src_action_id or not target_xml_id:
        return 0
    str_id = str(src_action_id)
    try:
        views = target_rpc.search_read(
            'ir.ui.view',
            [('arch', 'like', str_id)],
            ['id', 'arch'],
        )
    except Exception:
        return 0

    updated_count = 0
    for v in views:
        old_arch = v.get('arch') or ''
        new_arch = old_arch
        new_arch = re.sub(r'%\(' + str_id + r'\)d', f"%({target_xml_id})d", new_arch)
        new_arch = re.sub(
            r'(<button\b[^>]*\btype=["\']action["\'][^>]*\bname=)["\']' + str_id + r'["\']',
            r'\1"%(' + target_xml_id + r')d"',
            new_arch,
        )
        new_arch = re.sub(
            r'(<button\b[^>]*\bname=)["\']' + str_id + r'["\']([^>]*\btype=["\']action["\'])',
            r'\1"%(' + target_xml_id + r')d"\2',
            new_arch,
        )
        new_arch = re.sub(
            r'(\baction=)["\']' + str_id + r'["\']',
            r'\1"%(' + target_xml_id + r')d"',
            new_arch,
        )
        if new_arch != old_arch:
            try:
                target_rpc.write('ir.ui.view', [v['id']], {'arch': new_arch})
                updated_count += 1
            except Exception as e:
                _logger.warning("Could not update target view %s with action xml_id %s: %s", v['id'], target_xml_id, e)
    return updated_count


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
