/** @odoo-module **/

export function safeJson(raw, fallback = null) {
    if (!raw) return fallback;
    try {
        return JSON.parse(raw);
    } catch {
        return fallback;
    }
}

export function parseServerAction(raw) {
    if (!raw) {
        return {
            head: { name: '', state: '', model: '', binding_model: '', binding_type: '' },
            code: '',
            hasSeparator: false,
        };
    }

    const sepIndex = raw.indexOf('--- code ---');
    if (sepIndex === -1) {
        return {
            head: { name: '', state: '', model: '', binding_model: '', binding_type: '' },
            code: raw,
            hasSeparator: false,
        };
    }

    const headText = raw.slice(0, sepIndex);
    const code = raw.slice(sepIndex + '--- code ---'.length).replace(/^\n/, '');

    const head = { name: '', state: '', model: '', binding_model: '', binding_type: '' };
    headText.split('\n').forEach(line => {
        const m = line.match(/^([a-z_]+)\s*:\s*(.*)$/);
        if (m) {
            const k = m[1].trim();
            const v = m[2].trim();
            if (k in head) {
                head[k] = v;
            }
        }
    });

    return { head, code, hasSeparator: true };
}

export function parseSelection(val) {
    if (!val) return null;
    if (Array.isArray(val)) {
        return val.map(([k, label]) => ({ key: String(k), label: String(label) }));
    }
    if (typeof val === 'string') {
        const trimmed = val.trim();
        if (trimmed.startsWith('[') && trimmed.endsWith(']')) {
            const regex = /\(\s*['"]([^'"]*)['"]\s*,\s*['"]([^'"]*)['"]\s*\)/g;
            const items = [];
            let match;
            while ((match = regex.exec(trimmed)) !== null) {
                items.push({ key: match[1], label: match[2] });
            }
            if (items.length > 0) {
                return items;
            }
        }
        try {
            const parsed = JSON.parse(trimmed);
            if (Array.isArray(parsed)) {
                return parsed.map(([k, label]) => ({ key: String(k), label: String(label) }));
            }
        } catch {
            // Not JSON
        }
    }
    return null;
}

export function parseDepends(str) {
    if (!str) return [];
    if (Array.isArray(str)) return str;
    return str.split(',').map(s => s.trim()).filter(Boolean);
}

export function scanXmlTags(xml) {
    if (!xml) return [];
    const lines = xml.split('\n');
    const tags = [];
    const stack = [];

    const tagRegex = /<(\/?[A-Za-z_][\w.:-]*)([^<>]*?)(\/?)>/g;

    for (let lineIdx = 0; lineIdx < lines.length; lineIdx++) {
        const line = lines[lineIdx];
        const lineNum = lineIdx + 1;
        let match;
        while ((match = tagRegex.exec(line)) !== null) {
            const rawTag = match[1];
            const attrs = match[2];
            const selfClose = match[3] === '/' || rawTag.startsWith('?') || rawTag.startsWith('!');
            const isClosing = rawTag.startsWith('/');
            const tagName = isClosing ? rawTag.slice(1) : rawTag;

            if (isClosing) {
                if (stack.length) {
                    const top = stack.pop();
                    if (top.tag === tagName) {
                        top.endLine = lineNum;
                    }
                }
            } else if (selfClose) {
                const label = extractLabel(tagName, attrs);
                tags.push({
                    tag: tagName,
                    attrs: attrs.trim(),
                    line: lineNum,
                    endLine: lineNum,
                    depth: stack.length,
                    label,
                    foldable: false,
                });
            } else {
                const label = extractLabel(tagName, attrs);
                const item = {
                    tag: tagName,
                    attrs: attrs.trim(),
                    line: lineNum,
                    endLine: lineNum,
                    depth: stack.length,
                    label,
                    foldable: true,
                };
                tags.push(item);
                stack.push(item);
            }
        }
    }

    return tags;
}

function extractLabel(tag, attrs) {
    const attrMatch = (name) => {
        const re = new RegExp(`${name}=["']([^"']*)["']`);
        const m = attrs.match(re);
        return m ? m[1] : null;
    };

    if (tag === 'xpath') {
        const expr = attrMatch('expr');
        const pos = attrMatch('position');
        if (expr) {
            return pos ? `${expr} [${pos}]` : expr;
        }
    }
    const name = attrMatch('name');
    if (name) return name;
    const stringAttr = attrMatch('string');
    if (stringAttr) return stringAttr;
    const id = attrMatch('id');
    if (id) return id;
    return tag;
}

export function xmlWellFormed(xml) {
    if (!xml) return { valid: true, error: '' };
    try {
        const parser = new DOMParser();
        const doc = parser.parseFromString(xml, 'application/xml');
        const err = doc.querySelector('parsererror');
        if (err) {
            return { valid: false, error: err.textContent.trim().split('\n')[0] };
        }
        return { valid: true, error: '' };
    } catch (e) {
        return { valid: false, error: e.message };
    }
}

export function norm(v) {
    if (v === false || v === null || v === undefined || v === '') {
        return null;
    }
    if (typeof v === 'string') {
        const trimmed = v.trim();
        return trimmed === '' ? null : trimmed;
    }
    return v;
}

export function diffAttrs(oldObj = {}, newObj = {}, keys = null) {
    const allKeys = keys ? [...keys] : Array.from(new Set([...Object.keys(oldObj || {}), ...Object.keys(newObj || {})]));
    const rows = [];

    for (const key of allKeys) {
        const oldVal = (oldObj || {})[key];
        const newVal = (newObj || {})[key];
        const oldN = norm(oldVal);
        const newN = norm(newVal);

        const changed = oldN !== newN;
        const isAdded = oldN === null && newN !== null;
        const isRemoved = oldN !== null && newN === null;

        const label = key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
        rows.push({
            key,
            label,
            old: oldVal,
            new: newVal,
            changed,
            isAdded,
            isRemoved,
        });
    }

    return rows;
}
