# Ke hoach: UI approval render 100% tren Python (server-rendered)

> Doc nay bo sung cho `ORM_REFACTOR_PLAN.md` va `DEV_IMPLEMENTATION_PLAN.md`.
> No **thay the huong "Owl component nhan state lam props"** o Muc 6.2 cua
> `DEV_IMPLEMENTATION_PLAN.md` bang mot huong cuc doan hon theo yeu cau: JS
> khong tinh toan/quyet dinh bat ky thu gi, chi goi ORM va bom thang HTML
> Python tra ve vao DOM. Cac phan con lai (Muc 1-5, 7-10 cua 2 file kia:
> model, rule, execution, ACL, whitelist action/field) giu nguyen khong doi.

## 1. Nguyen tac

```text
Form load / save  ->  goi 1 ORM method  ->  Python:
                                              - tim process/execution
                                              - check quyen user
                                              - quyet dinh nut nao hien,
                                                enable/disable, label gi
                                              - RENDER LUON HTML (QWeb)
                                              -> tra ve 1 chuoi HTML
JS nhan chuoi HTML  ->  innerHTML vao 1 container co san trong DOM
                     ->  gan 1 delegated click listener DUY NHAT
                     ->  click -> doc data-action tren nut duoc click
                     ->  goi ORM execute method voi action do
                     ->  nhan HTML moi tra ve -> innerHTML lai
```

JS **khong** con:
- Cache process/step/rule.
- Tinh next/prev step.
- Tinh rule active, user duoc phep.
- Sinh chuoi HTML bang `btnGen()`/string concat.
- Quyet dinh nut nao show/hide/disable bang class CSS theo state.
- Tu ghi field/execution.

JS **chi con**:
- 1 ham `refresh()`: goi ORM, nhan HTML, gan vao container.
- 1 delegated click handler: doc `data-vp-action` tren phan tu duoc click,
  goi ORM action, roi `refresh()` lai (hoac dung luon HTML ma method action
  tra ve, khong can goi refresh rieng — xem Muc 3).
- Toggle 1-2 class tren cac nut native cua Odoo (Save/Discard/statusbar) dua
  tren 1 boolean rieng do Python tra ve (`lock_edit`, `lock_actions`) — day
  la thao tac DOM thuan tuy, khong phai quyet dinh nghiep vu (Python da
  quyet dinh, JS chi "thi hanh").

## 2. Vi sao dung QWeb (Python) thay vi string concat trong Python

Code hien tai dang dung `btnGen()` trong JS de noi chuoi HTML tay
(`Falinwa.validationProcess.js`, ham `btnGen`, `buildTemplate`,
`buildInfoBar`, `buildHistoryBar`). Chuyen dung logic nay sang Python nhung
**van noi chuoi f-string tay trong `.py`** se lap lai dung sai lam tuong tu
(de XSS neu ten step/rule co ky tu HTML, kho maintain, kho test).

De nghi dung **QWeb template** (co san trong Odoo, dung cho moi view/report)
thay vi noi chuoi trong `.py`:

- Tao file `views/approval_widget_templates.xml`, khai bao trong
  `assets_backend` hoac nhu view thuong (khong can render qua controller
  HTTP, chi can `ir.qweb`).
- Method Python goi:
  ```python
  html = self.env['ir.qweb']._render(
      'dn_oa_process.approval_action_bar',
      values,  # dict thuan, xem Muc 4
  )
  return str(html)
  ```
- QWeb tu dong escape moi `t-esc` (ten step, ten rule, ten process la Char
  field do admin nhap, van nen escape vi khong loai tru admin/nguoi cau
  hinh vo tinh go ky tu dac biet). Chi dung `t-raw`/`t-out` cho phan minh
  tu kiem soat hoan toan (icon class, id co dinh), khong bao gio `t-raw`
  cho gia tri Char field.
- Tai su dung nguyen id/class CSS da co trong `falinwa.scss`/`modern.css`
  (`#validationProcess_processActionBar`, `.validationProcess_actionBtn`,
  `validationProcess_green`, `validationProcess_red`, ...) de KHONG phai
  sua CSS — template QWeb chi can xuat dung cau truc HTML/class ma CSS hien
  co dang nham toi.

## 3. Method Python can co (thay the huong get_state/execute_action cu bang ban tra ve HTML)

Tren `fal.vprocess` (hoac 1 model helper rieng neu muon tach, vd
`fal.vprocess.ui`):

```python
@api.model
def render_approval_bar(self, model_name, res_id):
    """Tra ve {'html': <str>, 'lock_edit': bool, 'lock_actions': bool}.

    Gom toan bo logic cua get_approval_state (xem DEV_IMPLEMENTATION_PLAN
    Muc 2.2) + buoc render QWeb o cuoi. Khong tra rieng state dict ra
    ngoai cho JS doc/quyet dinh gi them — JS chi dung 'html' de bom vao
    DOM va 2 flag lock_* de toggle class tren nut native.
    """

@api.model
def execute_approval_action(self, model_name, res_id, action):
    """Nhu DEV_IMPLEMENTATION_PLAN Muc 2.3 (transition + business update +
    message/activity trong 1 transaction), nhung o buoc cuoi thay vi tra
    ve state dict, goi lai render_approval_bar(...) va tra ve cung dang
    {'html', 'lock_edit', 'lock_actions'}.

    => Tu 1 lan click, JS chi can 1 RPC (khong phai 2: action roi refresh),
    va luon nhan duoc HTML moi nhat, dam bao khong bao gio "quen" render
    lai sau action.
    """
```

Ca 2 method deu dung lai nguyen ven cac helper da lap ke hoach o
`ORM_REFACTOR_PLAN.md`/`DEV_IMPLEMENTATION_PLAN.md`:
`_get_process_for_model`, `_get_active_execution`, `vp_match`
(da co san), `get_allowed_user_ids` (da co san), `transition()` cua
execution. Doc nay chi doi **buoc cuoi cung** (tra HTML thay vi dict), khong
doi phan tim process/step/rule/quyen o giua.

## 4. Du lieu dua vao template (values dict) — Python quyet dinh het, template chi hien thi

```python
values = {
    'container_id': 'validationProcess_processActionBar',
    'state': 'checking|not_started|pending|awaiting_you|finished|cancelled|error',
    'buttons': [
        # Python da loc san: chi liet ke nut DUOC PHEP hien.
        # Template khong tu quyet dinh an/hien nut nao nua.
        {
            'action': 'confirm',      # -> data-vp-action="confirm"
            'label': 'Approve',
            'subtitle': step.name,     # escaped boi QWeb
            'color': 'green',
            'icon': 'check',
            'enabled': True,           # False = hien nhung disabled (vd dang xu ly)
        },
        {'action': 'back', 'label': 'Back', ...},
        {'action': 'cancel', 'label': 'Cancel', ...},
    ],
    'info_rows': [...],     # danh cho info bar, cung render server-side
    'history_rows': [...],  # danh cho history bar, cung render server-side
}
```

Diem mau chot: **template khong co `t-if` nao kiem tra quyen/step/rule**.
Toan bo dieu kien (co nut confirm hay khong, co bi disable hay khong, subtitle
la gi) da duoc Python tinh xong va dua thang vao `buttons` duoi dang list co
san. QWeb chi lap (`t-foreach`) qua list do va in ra — dung nghia "template
khong check gi ca", moi quyet dinh nam trong `render_approval_bar`.

## 5. JS con lai (toan bo, khong hon)

```js
/** @odoo-module */
// Container nay duoc dat san trong DOM boi 1 XML view them vao button_box,
// hoac boi formControllerPatch.js chen 1 lan duy nhat khi mounted.

async function refresh(orm, container, model, resId) {
    const res = await orm.call('fal.vprocess', 'render_approval_bar', [model, resId]);
    container.innerHTML = res.html;
    document.body.classList.toggle('validationProcess_lockEdit', !!res.lock_edit);
    document.body.classList.toggle('validationProcess_lockActions', !!res.lock_actions);
}

function bindClicks(orm, container, model, resId) {
    container.addEventListener('click', async (ev) => {
        const btn = ev.target.closest('[data-vp-action]');
        if (!btn || btn.disabled) return;
        const action = btn.dataset.vpAction;
        const res = await orm.call('fal.vprocess', 'execute_approval_action', [model, resId, action]);
        container.innerHTML = res.html;
        document.body.classList.toggle('validationProcess_lockEdit', !!res.lock_edit);
        document.body.classList.toggle('validationProcess_lockActions', !!res.lock_actions);
    });
}
```

Khong con: cache, `matchDomain`, `getActiveRules`, `checkIfAnyRuleIsActive`,
`filterRulesWhereUserIsAuthorized`, `createExecution`, `createExecutionStep`,
`btnGen`, `buildTemplate`, `buildInfoBar`, `buildHistoryBar`, vong lap
`watchUI`. Toan bo `Falinwa.validationProcess.js` (~2600 dong) co the xoa,
chi giu lai phan hook lifecycle (tuong duong
`Falinwa.formControllerPatch.js` hien co) goi `refresh()`/`bindClicks()`
mot lan khi mounted va sau moi lan save.

`document.body.classList.toggle(..., res.lock_edit)` van la 1 dong JS "thi
hanh" — no khong quyet dinh gi, chi doc dung boolean Python da tra ve va
ap dung. Day la ranh gioi hop ly nhat co the dat duoc: trinh duyet buoc
phai co it nhat 1 dong code doc gia tri va doi CSS class/DOM, nhung dong
do khong chua bat ky dieu kien nghiep vu nao.

## 6. Anh huong den lo trinh commit da co (DEV_IMPLEMENTATION_PLAN Muc 7)

Doc nay **khong doi Commit 0-2** (ACL, `get_approval_state`,
`execute_approval_action` phan business logic). No **thay the Commit 3 va 4**:

- Commit 3 (cu: "frontend goi state/action, giu UI hien tai qua Owl
  props") -> **thay bang**: Commit 3 lam `render_approval_bar` + QWeb
  template + JS rut gon nhu Muc 5, bo hoan toan Owl component cho action
  bar (khong can Owl o day nua vi HTML da render san).
- Commit 4 (cu: "Owl template cho approval bar/info/history") -> **khong
  can nua**, vi QWeb + innerHTML da thay the vai tro do. Neu sau nay muon
  animation/transition muot (nhu jQuery `.animate({opacity: toggle})` hien
  tai cho info/history bar), co the them CSS transition don gian
  (`transition: opacity .25s`) toggle bang 1 class, van khong can Owl hay
  logic JS them.

## 7. Danh doi (tradeoffs) can luu y

- **Uu diem**: dung 1 nguon rendering duy nhat, dung 1 lan security review
  (QWeb auto-escape + server tu quyet dinh nut), khong con nguy co
  "JS va Python lech nhau" (vd JS tuong buoc con nut nhung Python da chan).
  Debug de hon: `render_approval_bar` co the goi truc tiep tu Python
  shell/test va so sanh HTML tra ve.
- **Danh doi**: moi lan doi state phai load lai toan bo innerHTML cua
  container (khong con animation muot tung phan tu nhu jQuery cu, tru khi
  them CSS transition o Muc 6). Thay doi giao dien nut (them icon, doi bo
  cuc) gio phai sua file QWeb XML + có the them asset bundle, khong con
  sua truc tiep 1 file JS. Test UI can them buoc snapshot/regression cho
  HTML tra ve theo tung to hop state (xem Muc 8).

## 8. Test bo sung so voi DEV_IMPLEMENTATION_PLAN Muc 8

- Snapshot HTML cho tung state: `not_started`, `pending` (co/khong quyen),
  `awaiting_you` voi tung to hop nut (co/khong back, co/khong reset),
  `finished`, `cancelled`, moi truong hop 1 test rieng so sanh HTML dau ra
  (hoac it nhat so sanh danh sach `data-vp-action` xuat hien).
- Test rieng: ten step/rule chua ky tu `<script>`/`"` phai duoc escape dung
  trong HTML tra ve (khong bi injection).
- Test: `execute_approval_action` tra ve HTML da phan anh dung state MOI
  (khong phai state cu) ngay trong cung 1 response, khong can goi
  `render_approval_bar` lan 2 tu client.