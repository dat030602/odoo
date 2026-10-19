/** @odoo-module **/

const PY_KEYWORDS = new Set([
    'def', 'if', 'else', 'elif', 'for', 'in', 'return', 'import', 'from', 'class',
    'None', 'True', 'False', 'and', 'or', 'not', 'self', 'env', 'record', 'records',
    'raise', 'try', 'except', 'with', 'as', 'lambda', 'pass', 'is', 'while', 'break',
    'continue', 'yield', 'del', 'global', 'nonlocal', 'finally', 'assert',
]);

export function tokenize(line, lang = 'text') {
    if (!line) return [];
    if (line.length > 2000) {
        return [{ c: null, t: line }];
    }

    if (lang === 'xml') {
        return tokenizeXml(line);
    } else if (lang === 'python') {
        return tokenizePython(line);
    } else if (lang === 'json') {
        return tokenizeJson(line);
    }

    return [{ c: null, t: line }];
}

function tokenizeXml(line) {
    const tokens = [];
    // Tokenizer regex matching XML comments, tags, attributes, strings, text
    const re = /(<!--[\s\S]*?-->)|(<\/?[A-Za-z_][\w.:-]*)|(\/?>)|([a-zA-Z_:][\w.:-]*)(?=\s*=)|(".*?"|'.*?')|([^<>"']+)/g;
    let match;
    while ((match = re.exec(line)) !== null) {
        const [full, com, tag, closeTag, attr, str, text] = match;
        if (com) {
            tokens.push({ c: 'com', t: com });
        } else if (tag) {
            tokens.push({ c: 'tag', t: tag });
        } else if (closeTag) {
            tokens.push({ c: 'tag', t: closeTag });
        } else if (attr) {
            tokens.push({ c: 'attr', t: attr });
        } else if (str) {
            tokens.push({ c: 'str', t: str });
        } else if (text) {
            tokens.push({ c: null, t: text });
        } else {
            tokens.push({ c: null, t: full });
        }
    }
    return tokens.length ? tokens : [{ c: null, t: line }];
}

function tokenizePython(line) {
    const tokens = [];
    // Tokenizer regex matching comments, strings, identifiers, numbers, operators
    const re = /(#.*$)|("""[\s\S]*?"""|'''[\s\S]*?'''|".*?"|'.*?')|(\b\d+\.?\d*\b)|(\b[A-Za-z_]\w*\b)|(\s+|[^\s\w'"]+)/g;
    let match;
    while ((match = re.exec(line)) !== null) {
        const [full, com, str, num, ident, other] = match;
        if (com) {
            tokens.push({ c: 'com', t: com });
        } else if (str) {
            tokens.push({ c: 'str', t: str });
        } else if (num) {
            tokens.push({ c: 'num', t: num });
        } else if (ident) {
            if (PY_KEYWORDS.has(ident)) {
                tokens.push({ c: 'kw', t: ident });
            } else {
                tokens.push({ c: null, t: ident });
            }
        } else if (other) {
            tokens.push({ c: null, t: other });
        } else {
            tokens.push({ c: null, t: full });
        }
    }
    return tokens.length ? tokens : [{ c: null, t: line }];
}

function tokenizeJson(line) {
    const tokens = [];
    const re = /("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*")(?=\s*:)|("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*")|(-?\d+\.?\d*(?:[eE][+-]?\d+)?)|(\btrue\b|\bfalse\b|\bnull\b)|(\s+|[{}\[\],:])/g;
    let match;
    while ((match = re.exec(line)) !== null) {
        const [full, key, _k1, str, _s1, num, kw, other] = match;
        if (key) {
            tokens.push({ c: 'attr', t: key });
        } else if (str) {
            tokens.push({ c: 'str', t: str });
        } else if (num) {
            tokens.push({ c: 'num', t: num });
        } else if (kw) {
            tokens.push({ c: 'kw', t: kw });
        } else if (other) {
            tokens.push({ c: null, t: other });
        } else {
            tokens.push({ c: null, t: full });
        }
    }
    return tokens.length ? tokens : [{ c: null, t: line }];
}
