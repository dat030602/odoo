# Odoo 20 OWL Guide

Guide for building OWL 3 (Owl Web Library) components in Odoo 20.

## Table of Contents

- [OWL 3 Overview](#owl-3-overview)
- [Component Structure](#component-structure)
- [Props Declaration with `useProps` and `t`](#props-declaration-with-useprops-and-t)
- [State Management (`proxy` & Signals)](#state-management-proxy--signals)
- [DOM References (`signal.ref`)](#dom-references-signalref)
- [Plugins (Replacing Services)](#plugins-replacing-services)
- [QWeb Templates in OWL 3](#qweb-templates-in-owl-3)
- [Lifecycle Hooks](#lifecycle-hooks)
- [Testing Components with `@odoo/hoot`](#testing-components-with-odoohoot)

---

## OWL 3 Overview

Odoo 20 runs on **Owl 3**, bringing major architectural improvements over Owl 2:

| Area | Owl 2 (Odoo 19 & earlier) | Owl 3 (Odoo 20) |
|------|---------------------------|-----------------|
| **Props** | Static `props = { ... }` | Field declaration `props = useProps({ ... })` with `t` schema |
| **Component State** | `useState({ ... })` | `this.state = proxy({ ... })` |
| **Fine-grained Reactivity** | Deep proxy reactivity | **Signals** (`signal()`, `computed()`, `signal.ref()`) |
| **Services / Plugins** | `this.action = useService('action')` | Class field `action = usePlugin(ActionPlugin)` |
| **Templates Variables** | `<t t-esc="myVar"/>` without `this.` | `<t t-out="this.myVar"/>` (must use `this.`) |
| **Slot Directive** | `<t t-slot="default"/>` | `<t t-call-slot="default"/>` |
| **DOM Refs** | `useRef("myRef")` | `myRef = signal.ref();` + `t-ref="this.myRef"` |
| **JS Unit Tests** | QUnit / legacy helpers | **`@odoo/hoot`** test framework |

---

## Component Structure

### Basic Component Example

File: `static/src/components/counter/counter.js`

```javascript
import { Component, onMounted, proxy, signal, t, usePlugin, useProps } from "@odoo/owl";
import { NotificationPlugin } from "@web/core/notifications/notification_plugin";

export const counterProps = {
    initialCount: t.number().optional(0),
    title: t.string().optional("Counter"),
    onIncrement: t.function().optional(),
};

export class Counter extends Component {
    static template = "my_module.Counter";
    props = useProps(counterProps);

    // Plugins declared as class fields
    notification = usePlugin(NotificationPlugin);

    // DOM ref as signal
    buttonRef = signal.ref();

    setup() {
        super.setup();
        this.state = proxy({
            count: this.props.initialCount,
        });

        onMounted(() => {
            if (this.buttonRef()) {
                this.buttonRef().focus();
            }
        });
    }

    increment() {
        this.state.count++;
        this.notification.add(`Count is now ${this.state.count}`, { type: "info" });
        if (this.props.onIncrement) {
            this.props.onIncrement(this.state.count);
        }
    }
}
```

---

## Props Declaration with `useProps` and `t`

In Owl 3, static `props` objects are ignored. Props must be declared using `useProps()` and validated using the `t` type builder from `@odoo/owl`.

```javascript
import { Component, t, useProps } from "@odoo/owl";

export const userCardProps = {
    // Basic types
    name: t.string(),
    age: t.number().optional(18),
    isAdmin: t.boolean().optional(false),

    // Relational / collections
    tags: t.array(t.string()).optional([]),
    settings: t.object().optional({}),

    // Callbacks & functions
    onSave: t.function().optional(),

    // Flexible / generic
    slots: t.object().optional(),
    customData: t.any().optional(),

    // Signals & refs
    targetRef: t.signal(t.ref()).optional(),
};

export class UserCard extends Component {
    static template = "my_module.UserCard";
    props = useProps(userCardProps);
}
```

### Common `t` Type Validators

- `t.string()`: String value (`.optional(default)`)
- `t.number()`: Numeric value
- `t.boolean()`: Boolean flag
- `t.array(elementType)`: Array of elements
- `t.object(shape)`: Dictionary / object
- `t.function()`: Callable function
- `t.any()`: Unrestricted value
- `t.ref()`: HTMLElement reference
- `t.signal(innerType)`: Reactive signal

---

## State Management (`proxy` & Signals)

### 1. `proxy(...)` (Replaces `useState`)

For reactive state objects, use `proxy(...)`:

```javascript
setup() {
    super.setup();
    this.state = proxy({
        searchTerm: "",
        items: [],
        isLoading: false,
    });
}
```

Updating properties directly triggers component re-renders:
```javascript
this.state.searchTerm = "test";
this.state.items.push(newItem);
```

### 2. Signals (`signal()`, `computed()`)

Signals provide fine-grained reactivity:

```javascript
import { Component, signal, computed } from "@odoo/owl";

export class SignalComponent extends Component {
    static template = "my_module.SignalComponent";

    // Create a signal
    count = signal(0);

    // Derived computed signal
    doubleCount = computed(() => this.count() * 2);

    increment() {
        // Read via this.count()
        // Write by passing new value: this.count.set(value) or mutating
        this.count.set(this.count() + 1);
    }
}
```

---

## DOM References (`signal.ref`)

In Owl 3, DOM elements are referenced using `signal.ref()`:

### JavaScript
```javascript
import { Component, signal, onMounted } from "@odoo/owl";

export class SearchInput extends Component {
    static template = "my_module.SearchInput";

    inputRef = signal.ref();

    setup() {
        super.setup();
        onMounted(() => {
            // Access the element by calling the ref signal:
            const el = this.inputRef();
            if (el) {
                el.focus();
            }
        });
    }
}
```

### QWeb Template
```xml
<t t-name="my_module.SearchInput">
    <div class="search-box">
        <input type="text" t-ref="this.inputRef" class="form-control"/>
    </div>
</t>
```

---

## Plugins (Replacing Services)

In Owl 3, component services are implemented as **Plugins** and injected via `usePlugin(PluginClass)` as class fields.

### Common Odoo 20 Plugins

| Service / Capability | Plugin Class | Import Path |
|----------------------|--------------|-------------|
| **ORM calls** | `ORM` | `@web/core/orm_service` (or `@web/core/orm_plugin`) |
| **Action Manager** | `ActionPlugin` | `@web/webclient/actions/action_plugin` |
| **Notifications** | `NotificationPlugin` | `@web/core/notifications/notification_plugin` |
| **Dialogs & Modals** | `DialogPlugin` | `@web/core/dialog/dialog_plugin` |
| **UI Environment** | `UIPlugin` | `@web/core/ui/ui_plugin` |
| **Hotkeys** | `HotkeyPlugin` | `@web/core/hotkeys/hotkey_plugin` |
| **Currencies** | `CurrencyPlugin` | `@web/webclient/currency_plugin` |

### Using Plugins in Components

```javascript
import { Component, usePlugin } from "@odoo/owl";
import { ActionPlugin } from "@web/webclient/actions/action_plugin";
import { NotificationPlugin } from "@web/core/notifications/notification_plugin";
import { ORM } from "@web/core/orm_service";

export class PartnerViewer extends Component {
    static template = "my_module.PartnerViewer";

    // Direct class field declarations
    action = usePlugin(ActionPlugin);
    notification = usePlugin(NotificationPlugin);
    orm = usePlugin(ORM);

    async openPartner(partnerId) {
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "res.partner",
            res_id: partnerId,
            views: [[false, "form"]],
        });
    }
}
```

---

## QWeb Templates in OWL 3

### Critical Rules in OWL 3 Templates:
1. **Always use `this.` prefix**: Component variables, state, and methods MUST be referenced via `this.` (e.g. `this.state.x`, `this.props.y`, `this.handleClick`).
2. **Use `<t t-call-slot="name"/>`**: Never use `<t t-slot="..."/>`.
3. **Use `<t t-out="..."/>`**: Never use `<t t-esc="..."/>`.
4. **Bind refs with `t-ref="this.refName"`**.

### Example Template

File: `static/src/components/counter/counter.xml`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<templates xml:space="preserve">

    <t t-name="my_module.Counter">
        <div class="card p-3 my-counter" t-att-class="{ 'border-primary': this.state.count > 0 }">
            <h4 t-out="this.props.title"/>
            <p>Current count: <strong t-out="this.state.count"/></p>

            <div class="btn-group">
                <button
                    class="btn btn-primary"
                    t-ref="this.buttonRef"
                    t-on-click="this.increment"
                >
                    Increment
                </button>
            </div>

            <!-- Slots -->
            <div class="counter-footer mt-2">
                <t t-call-slot="default">
                    <small class="text-muted">Default footer content</small>
                </t>
            </div>
        </div>
    </t>

</templates>
```

---

## Lifecycle Hooks

Owl 3 provides the following lifecycle hooks from `@odoo/owl`:

```javascript
import {
    Component,
    onWillStart,
    onMounted,
    onWillPatch,
    onPatched,
    onWillUnmount,
    onWillUpdateProps,
    onError,
    useOnChange,
    useListener,
} from "@odoo/owl";

export class LifecycleDemo extends Component {
    static template = "my_module.LifecycleDemo";

    setup() {
        super.setup();

        // Async preparation before rendering
        onWillStart(async () => {
            this.initialData = await this.loadData();
        });

        // DOM mounted
        onMounted(() => {
            console.log("Mounted to DOM");
        });

        // Props updated from parent
        onWillUpdateProps((nextProps) => {
            console.log("Props will update:", nextProps);
        });

        // DOM patched
        onPatched(() => {
            console.log("DOM updated");
        });

        // Component destruction
        onWillUnmount(() => {
            console.log("Cleaning up");
        });

        // Reactive changes watcher
        useOnChange(
            () => [this.props.filterId],
            ([filterId]) => {
                this.reloadFiltered(filterId);
            }
        );

        // Window / DOM event listener
        useListener(window, "resize", () => this.handleResize());
    }
}
```

---

## Testing Components with `@odoo/hoot`

In Odoo 20, JS unit tests are written with **`@odoo/hoot`** and `@web/../tests/web_test_helpers`.

File: `static/tests/counter.test.js`

```javascript
import { expect, test } from "@odoo/hoot";
import { contains, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { Counter } from "../components/counter/counter";

test("Counter increments on button click", async () => {
    await mountWithCleanup(Counter, {
        props: {
            initialCount: 5,
            title: "Test Counter",
        },
    });

    expect(".my-counter h4").toHaveText("Test Counter");
    expect(".my-counter strong").toHaveText("5");

    await contains("button").click();

    expect(".my-counter strong").toHaveText("6");
});
```

