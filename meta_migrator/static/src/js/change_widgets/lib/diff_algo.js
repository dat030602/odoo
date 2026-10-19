/** @odoo-module **/

export function diffLines(oldText, newText) {
    const normA = (oldText || '').replace(/\r\n|\r/g, '\n');
    const normB = (newText || '').replace(/\r\n|\r/g, '\n');
    const A = normA ? normA.split('\n') : [];
    const B = normB ? normB.split('\n') : [];

    let s = 0;
    while (s < A.length && s < B.length && A[s] === B[s]) {
        s++;
    }
    let ea = A.length;
    let eb = B.length;
    while (ea > s && eb > s && A[ea - 1] === B[eb - 1]) {
        ea--;
        eb--;
    }
    const ops = [];
    for (let i = 0; i < s; i++) {
        ops.push({ t: 'eq', a: i + 1, b: i + 1, text: A[i] });
    }
    ops.push(...lcsDiff(A.slice(s, ea), B.slice(s, eb), s));
    for (let k = 0; k < A.length - ea; k++) {
        ops.push({ t: 'eq', a: ea + k + 1, b: eb + k + 1, text: A[ea + k] });
    }
    return ops;
}

function lcsDiff(X, Y, off) {
    const n = X.length;
    const m = Y.length;
    const out = [];
    if (!n || !m || n * m > 4e6) {
        X.forEach((t, i) => out.push({ t: 'del', a: off + i + 1, b: null, text: t }));
        Y.forEach((t, j) => out.push({ t: 'add', a: null, b: off + j + 1, text: t }));
        return out;
    }
    const w = m + 1;
    const L = new Uint32Array((n + 1) * w);
    for (let i = n - 1; i >= 0; i--) {
        for (let j = m - 1; j >= 0; j--) {
            L[i * w + j] = X[i] === Y[j] ? L[(i + 1) * w + j + 1] + 1
                                         : Math.max(L[(i + 1) * w + j], L[i * w + j + 1]);
        }
    }
    let i = 0;
    let j = 0;
    while (i < n && j < m) {
        if (X[i] === Y[j]) {
            out.push({ t: 'eq', a: off + i + 1, b: off + j + 1, text: X[i] });
            i++;
            j++;
        } else if (L[(i + 1) * w + j] >= L[i * w + j + 1]) {
            out.push({ t: 'del', a: off + i + 1, b: null, text: X[i] });
            i++;
        } else {
            out.push({ t: 'add', a: null, b: off + j + 1, text: Y[j] });
            j++;
        }
    }
    for (; i < n; i++) {
        out.push({ t: 'del', a: off + i + 1, b: null, text: X[i] });
    }
    for (; j < m; j++) {
        out.push({ t: 'add', a: null, b: off + j + 1, text: Y[j] });
    }
    return out;
}

export function foldOps(ops, ctx = 3, opened = {}) {
    if (!ops || !ops.length) return [];
    const hasDiff = ops.some(o => o.t !== 'eq');
    if (!hasDiff) {
        return ops;
    }

    const keep = new Array(ops.length).fill(false);
    ops.forEach((o, i) => {
        if (o.t !== 'eq') {
            const start = Math.max(0, i - ctx);
            const end = Math.min(ops.length - 1, i + ctx);
            for (let k = start; k <= end; k++) {
                keep[k] = true;
            }
        }
    });

    const rows = [];
    for (let i = 0; i < ops.length; i++) {
        if (keep[i] || opened[i]) {
            rows.push({ ...ops[i], id: i });
            continue;
        }
        let j = i;
        while (j < ops.length && !keep[j] && !opened[j]) {
            j++;
        }
        const count = j - i;
        if (count > 0) {
            rows.push({ t: 'fold', id: i, count });
            i = j - 1;
        }
    }
    return rows;
}

export function changeBlocks(ops) {
    if (!ops || !ops.length) return [];
    const blocks = [];
    let inChange = false;
    for (let i = 0; i < ops.length; i++) {
        if (ops[i].t !== 'eq') {
            if (!inChange) {
                blocks.push(i);
                inChange = true;
            }
        } else {
            inChange = false;
        }
    }
    return blocks;
}

export function stats(ops) {
    if (!ops) return { added: 0, removed: 0 };
    return {
        added: ops.filter(o => o.t === 'add').length,
        removed: ops.filter(o => o.t === 'del').length,
    };
}

export function wordDiff(lineA, lineB) {
    if (!lineA && !lineB) return { left: [], right: [] };
    if (!lineA) return { left: [], right: [{ t: 'add', text: lineB, w: true }] };
    if (!lineB) return { left: [{ t: 'del', text: lineA, w: true }], right: [] };

    if (lineA.length > 500 || lineB.length > 500) {
        return {
            left: [{ t: 'del', text: lineA, w: false }],
            right: [{ t: 'add', text: lineB, w: false }],
        };
    }

    const tokenize = (str) => str.match(/(\s+|[A-Za-z0-9_]+|[^\s\w])/g) || [];
    const tokensA = tokenize(lineA);
    const tokensB = tokenize(lineB);

    if (tokensA.length > 500 || tokensB.length > 500 || tokensA.length * tokensB.length > 250000) {
        return {
            left: [{ t: 'del', text: lineA, w: false }],
            right: [{ t: 'add', text: lineB, w: false }],
        };
    }

    const n = tokensA.length;
    const m = tokensB.length;
    const w = m + 1;
    const L = new Uint16Array((n + 1) * w);

    for (let i = n - 1; i >= 0; i--) {
        for (let j = m - 1; j >= 0; j--) {
            L[i * w + j] = tokensA[i] === tokensB[j] ? L[(i + 1) * w + j + 1] + 1
                                                     : Math.max(L[(i + 1) * w + j], L[i * w + j + 1]);
        }
    }

    const left = [];
    const right = [];
    let i = 0;
    let j = 0;

    while (i < n && j < m) {
        if (tokensA[i] === tokensB[j]) {
            left.push({ t: 'eq', text: tokensA[i], w: false });
            right.push({ t: 'eq', text: tokensB[j], w: false });
            i++;
            j++;
        } else if (L[(i + 1) * w + j] >= L[i * w + j + 1]) {
            left.push({ t: 'del', text: tokensA[i], w: true });
            i++;
        } else {
            right.push({ t: 'add', text: tokensB[j], w: true });
            j++;
        }
    }
    for (; i < n; i++) {
        left.push({ t: 'del', text: tokensA[i], w: true });
    }
    for (; j < m; j++) {
        right.push({ t: 'add', text: tokensB[j], w: true });
    }

    return { left, right };
}

export function pairRows(ops) {
    if (!ops || !ops.length) return [];
    const pairs = [];
    let i = 0;
    while (i < ops.length) {
        const op = ops[i];
        if (op.t === 'eq') {
            pairs.push({
                t: 'eq',
                left: { n: op.a, text: op.text, t: 'eq' },
                right: { n: op.b, text: op.text, t: 'eq' },
            });
            i++;
        } else {
            const dels = [];
            const adds = [];
            while (i < ops.length && ops[i].t !== 'eq') {
                if (ops[i].t === 'del') {
                    dels.push(ops[i]);
                } else if (ops[i].t === 'add') {
                    adds.push(ops[i]);
                }
                i++;
            }
            const count = Math.max(dels.length, adds.length);
            for (let k = 0; k < count; k++) {
                const delOp = dels[k] || null;
                const addOp = adds[k] || null;
                let wTokens = null;
                if (delOp && addOp) {
                    wTokens = wordDiff(delOp.text, addOp.text);
                }
                pairs.push({
                    t: 'change',
                    left: delOp ? {
                        n: delOp.a,
                        text: delOp.text,
                        t: 'del',
                        wordTokens: wTokens ? wTokens.left : null,
                    } : null,
                    right: addOp ? {
                        n: addOp.b,
                        text: addOp.text,
                        t: 'add',
                        wordTokens: wTokens ? wTokens.right : null,
                    } : null,
                });
            }
        }
    }
    return pairs;
}
