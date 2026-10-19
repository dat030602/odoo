/** @odoo-module **/

export const TYPE_GROUP_MAP = {
    char: 'text',
    text: 'text',
    html: 'text',
    integer: 'num',
    float: 'num',
    monetary: 'num',
    boolean: 'bool',
    date: 'date',
    datetime: 'date',
    many2one: 'rel',
    one2many: 'rel',
    many2many: 'rel',
    selection: 'sel',
    binary: 'bin',
    image: 'bin',
};

export function getTypeGroup(ttype) {
    return TYPE_GROUP_MAP[ttype] || 'other';
}

export const FIELD_GROUPS = [
    {
        id: 'basic',
        label: 'Basic',
        keys: ['name', 'field_description', 'ttype', 'help'],
    },
    {
        id: 'constraints',
        label: 'Constraints',
        keys: ['required', 'readonly', 'store', 'index', 'copied', 'translate'],
    },
    {
        id: 'relation',
        label: 'Relation',
        keys: ['relation', 'relation_field', 'on_delete', 'domain'],
    },
    {
        id: 'selection',
        label: 'Selection',
        wide: true,
        keys: ['selection'],
    },
    {
        id: 'logic',
        label: 'Logic',
        wide: true,
        keys: ['compute', 'depends', 'related'],
    },
];

export const MODEL_FIELDS_COLUMNS = [
    { key: 'name', label: 'Name', kind: 'text', defaultVisible: true, sticky: true },
    { key: 'field_description', label: 'Label', kind: 'text', defaultVisible: true },
    { key: 'ttype', label: 'Type', kind: 'type', defaultVisible: true },
    { key: 'required', label: 'Req', kind: 'bool', defaultVisible: true },
    { key: 'store', label: 'Store', kind: 'bool', defaultVisible: true },
    { key: 'relation', label: 'Relation', kind: 'model', defaultVisible: true },
    { key: 'compute', label: 'Compute', kind: 'code', defaultVisible: true },
    { key: 'readonly', label: 'Readonly', kind: 'bool', defaultVisible: false },
    { key: 'index', label: 'Index', kind: 'bool', defaultVisible: false },
    { key: 'copied', label: 'Copied', kind: 'bool', defaultVisible: false },
    { key: 'translate', label: 'Translate', kind: 'bool', defaultVisible: false },
    { key: 'relation_field', label: 'Rel Field', kind: 'text', defaultVisible: false },
    { key: 'on_delete', label: 'On Delete', kind: 'text', defaultVisible: false },
    { key: 'depends', label: 'Depends', kind: 'chips', defaultVisible: false },
    { key: 'related', label: 'Related', kind: 'text', defaultVisible: false },
];
