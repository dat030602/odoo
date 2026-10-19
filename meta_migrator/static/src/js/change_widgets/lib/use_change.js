/** @odoo-module **/

export function useChange(props) {
    const cache = {};
    const parse = (key, raw, fallback) => {
        if (cache[key]?.raw === raw) return cache[key].val;
        let val = fallback;
        try {
            val = raw ? JSON.parse(raw) : fallback;
        } catch {
            // Keep fallback on error
        }
        cache[key] = { raw, val };
        return val;
    };
    const d = () => props.record.data;

    return {
        get changeType() {
            return d().change_type;
        },
        get objectType() {
            return d().object_type;
        },
        get status() {
            return d().status;
        },
        get message() {
            return d().message || '';
        },
        get targetRef() {
            return d().target_ref || '';
        },
        get newRaw() {
            return d()[props.name] || '';
        },
        get oldRaw() {
            return d().old_raw || '';
        },
        get extraRaw() {
            return d().extra_raw || '';
        },
        get newObj() {
            return parse('n', this.newRaw, {});
        },
        get oldObj() {
            return parse('o', this.oldRaw, {});
        },
        get extra() {
            return parse('e', d().extra_raw, {});
        },
        get children() {
            return parse('c', d().children_json, []);
        },
    };
}
