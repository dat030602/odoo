# Ke hoach dev implementation

> **Cap nhat sau khi doc code hien tai (26/08/2026):** chi tiet doi chieu
> nam o **Muc 10** cuoi file `ORM_REFACTOR_PLAN.md`. Ba diem anh huong truc
> tiep den ke hoach commit ben duoi:
> 1. `security/ir.model.access.csv` dang cho **moi user** full
>    read/write/create/unlink tren ca 4 model (`fal.vprocess*`), ke ca
>    `fal.vprocess.execution`. Day la lo hong nghiem trong, doc lap voi
>    refactor — them **Commit 0** o Muc 7 de fix truoc.
> 2. Da co san `fal.vprocess.vp_match()` va
>    `fal.vprocess.rule.get_allowed_user_ids()` — day chinh la phoi thai cua
>    `_match_filters` (Muc 2.1) va `get_authorized_users`/`is_user_authorized`
>    (Muc 4). **Tai su dung**, dung viet lai tu dau.
> 3. Da co `Falinwa.formControllerPatch.js` hook `onMounted`/`onRecordSaved`,
>    nhung file JS cu (`Falinwa.validationProcess.js`) van con vong lap
>    `setInterval` 250ms (`watchUI`) chay song song va cung goi
>    `onDocumentChanged`. Commit 3 (Muc 7) phai **bo han `watchUI`**, khong
>    chi them RPC moi ben canh no.

## 1. Nguyen tac chinh

Chuyen logic quyet dinh approval tu JavaScript sang Python ORM. Frontend khong tu tinh domain, rule, user permission hoac step transition.

Frontend chi lam ba viec:

1. Goi ORM khi form duoc mo hoac sau khi save.
2. Render cac nut theo state server tra ve.
3. Goi ORM khi nguoi dung bam nut va render lai state moi.

## 2. Thay doi tren model `fal.vprocess`

File: `models/fal_vprocess.py`

### 2.1. Tao helper tim process

Du kien them cac method noi bo:

```python
_get_process_for_model(model_name)
_get_record(model_name, record_id)
_match_filters(record, filter_ids)
_get_active_execution(process, record_id)
```

Yeu cau:

- Kiem tra model ton tai trong registry.
- Kiem tra record ton tai va user co quyen doc.
- Chi lay process active va co step active.
- Xu ly ro rang truong hop co nhieu process cho cung model.
- Dung domain ORM thay vi parse domain tai client.

**Da co san, tai su dung thay vi viet lai:** `fal.vprocess.vp_match(model,
res_id, filter_ids)` da lam dung viec cua `_match_filters` (AND domain cua
nhieu `ir.filters` bang `search_count`, tren `sudo()`). `_get_process_for_model`
va `_get_active_execution` van can viet moi (chua co), nhung nen goi
`vp_match` ben trong thay vi viet lai logic AND-domain.

### 2.2. Tao method lay state

Du kien:

```python
get_approval_state(model_name, record_id)
```

State tra ve nen co dang tuong tu:

```python
{
    "has_process": True,
    "started": True,
    "execution_id": 10,
    "process_id": 3,
    "step_id": 5,
    "step_name": "Manager approval",
    "is_final": False,
    "is_cancelled": False,
    "can_approve": True,
    "can_edit": False,
    "can_use_actions": False,
    "buttons": ["confirm", "back", "cancel"],
    "next_step_id": 6,
    "previous_step_id": 4,
}
```

Method nay se gom logic dang nam trong `onDocumentChanged`, `getActiveRules`, `checkIfAnyRuleIsActive` va cac ham loc user cua JS.

Neu chua co execution va record match trigger, method co the tao execution dau tien trong ORM. Can dam bao viec tao execution la idempotent va khong tao trung khi co hai request dong thoi.

### 2.3. Tao method xu ly action

Du kien:

```python
execute_approval_action(model_name, record_id, action)
```

Flow:

1. Validate `action` nam trong tap `confirm`, `cancel`, `back`, `restart`.
2. Tim process va execution bang server-side logic.
3. Lock execution dang xu ly hoac doc lai trang thai trong transaction.
4. Kiem tra user co quyen voi step hien tai.
5. Kiem tra action duoc phep theo cau hinh step.
6. Xac dinh step moi va trang thai `finished`/`cancelled`.
7. Chay business update bang helper co whitelist.
8. Ghi execution.
9. Tao message/activity neu cau hinh yeu cau.
10. Tra ve `get_approval_state(...)` sau khi cap nhat.

## 3. Chuan hoa update business record

File de xem xet: `models/fal_vprocess_step.py` hoac tao model helper rieng.

### 3.1. Khong cho phep client tu gui code thuc thi

Khong tiep tuc cho JS truyen truc tiep ten method/field roi ORM goi tuy y.

Thay vao do, chon mot trong hai cach:

- Cach A: cau hinh action/field duoc validate khi luu process.
- Cach B: tao whitelist theo model, action va field trong Python.

Neu van giu field string, can parse va validate tai server:

- Field phai ton tai.
- Field phai writable.
- Gia tri phai dung kieu du lieu.
- Khong cho cap nhat field ky thuat hoac field quan trong neu khong co rule rieng.

Neu van giu action string, method phai nam trong whitelist va duoc goi tren recordset dung access rights.

### 3.2. Dung recordset thay vi RPC tung record

Business action nen nhan recordset, vi du `records.action_confirm()`, thay vi de JS goi method voi mot integer id. Viec nay giup giu access check va transaction trong ORM.

## 4. Chuan hoa rule va quyen

File: `models/fal_vprocess_rule.py`

Tao method noi bo, vi du:

```python
get_authorized_users(record)
is_user_authorized(record, user=None)
matches_record(record)
```

Yeu cau:

- Rule custom rong user list: xu ly theo cau hinh `allow_anyone_no_conditions`.
- Rule domain: evaluate domain server-side.
- Rule server action: chi chay action hop le va ket qua phai duoc normalize thanh user IDs.
- Chi tinh rule active va match record hien tai.
- Khong dua danh sach user day du ra client neu chi can ket qua boolean.

**Da co san, tai su dung thay vi viet lai:** `get_allowed_user_ids()` da xu
ly ca 3 `user_domain_type` (`custom`/`domain`/`server`), da `safe_eval` domain
va normalize ket qua server action thanh user IDs. Coi day la phan loi cua
`get_authorized_users`; `is_user_authorized(record, user=None)` chi can goi
`get_allowed_user_ids()` roi kiem tra `user.id in ids` (tra ve boolean, khong
lo danh sach ra ngoai). `matches_record(record)` van can viet moi, nen goi
`vp_match`/`_match_filters` cua `fal.vprocess` cho field `filter_id` cua rule.

## 5. Refactor execution model

File: `models/fal_vprocess_execution.py`

### 5.1. Them constraint

Xem xet SQL constraint hoac helper de gioi han mot execution active cho moi cap `(process_id, process_model, target)`.

Neu khong the dung unique constraint vi co nhieu ban ghi lich su, phai dung transaction lock va search lai truoc khi create.

### 5.2. Them method chuyen buoc

Du kien:

```python
transition(action, acting_user=None)
```

Method nay chi chuyen trang thai execution. Business update, message va activity co the duoc goi tu service ORM cung transaction.

Can ghi ro `previous_step_id`, `last_action`, `finished`, `cancelled` va step tiep theo hoac step quay lai.

## 6. Frontend sau khi refactor

File can sua:

- `static/src/js/Falinwa/Falinwa.formControllerPatch.js`
- `static/src/js/Falinwa/Falinwa.validationProcess.js`

### 6.1. Form controller

Giu hook `onMounted` va `onRecordSaved`, nhung thay noi dung xu ly bang mot RPC lay state `get_approval_state(resModel, resId)`.

Khong can bootstrap toan bo process/rule vao `session_info` neu khong con logic client phai suy dien.

**Ghi chu hien trang:** `Falinwa.formControllerPatch.js` da ton tai va da
hook dung `onWillStart`/`onMounted`/`onRecordSaved` — chi can doi noi dung
ben trong tu goi `onDocumentChanged` (engine cu) sang goi
`get_approval_state`. Nhung `Falinwa.validationProcess.js` van con vong lap
`watchUI` (`setInterval` 250ms doc URL param) tu goi lai `onDocumentChanged`
song song — **phai bo han vong lap nay** trong commit nay, khong de no chay
song song voi RPC moi (hien tai ca hai co che dang chay cung luc va co the
goi trung state 2 lan). Tuong tu, bo dan viec doc `session.vprocess_bootstrap`
va `session.vprocess_models` (`ir_http.py`) mot khi frontend khong con doc
truc tiep config o client nua; co the giu tam `vprocess_models` chi de
quyet dinh co hien loading overlay tu `onWillStart` hay khong (UX), khong
dung de suy luan nghiep vu.

### 6.2. Approval component

Co the giu class `ValidationProcess` trong buoc migration dau tien, sau do chuyen phan render sang Owl component/template.

Component chi nhan `state`, `onAction` va `onRefresh` lam props. Component khong duoc tu goi business method, tu ghi field, tu quyet dinh quyen hoac tu chuyen step.

### 6.3. Trang thai loading va loi

Can co cac state `checking`, `not_started`, `pending`, `finished`, `cancelled` va `error`.

## 7. Lo trinh commit de code

### Commit 0: Fix ACL (lam truoc tien, tach rieng khoi refactor)

- Sua `security/ir.model.access.csv`: bo `perm_write`/`perm_create`/
  `perm_unlink` cho `base.group_user` tren ca 4 model
  (`fal.vprocess`, `.step`, `.rule`, `.execution`), chi giu `perm_read`.
- Tao nhom quan tri rieng (hoac dung nhom admin co san) giu full CRUD cho
  cau hinh (`fal.vprocess`/`.step`/`.rule`), phuc vu backend config.
- Kiem tra lai cac cho JS dang `write`/`create` truc tiep (`createUpdate`,
  `createExecution`, `createExecutionStep`) — sau khi sua ACL cac cho nay se
  loi quyen ngay lap tuc (dung nhu mong muon); day la tin hieu de xac nhan
  ACL da duoc sua dung, nhung cung co nghia **commit nay phai lam ngay truoc
  Commit 1**, hoac Commit 1/2 phai duoc trien khai gan nhu dong thoi de
  khong lam gian doan workflow approval dang chay that.
- Khong can test rieng cho commit nay ngoai smoke test: user thuong khong
  con ghi truc tiep duoc `fal.vprocess.execution` qua RPC/console.

### Commit 1: ORM read-only state

- Them helper tim process/filter/execution.
- Them `get_approval_state`.
- Chua bo logic cu cua JS.
- Viet test state cho cac truong hop co ban.

### Commit 2: ORM action transaction

- Them `execute_approval_action`.
- Chuyen transition, field update, business action, message va activity vao server.
- Them authorization va concurrency check.
- Viet test thanh cong va rollback.
- Luu y tuong thich nguoc: `action_string_*` hien la chuoi ten method cach
  nhau boi dau phay (goi lan luot voi `[res_id]`), `field_string_*` hien la
  chuoi `field=value,field2=value2` khong ep kieu. Server whitelist (Muc 3)
  phai parse dung dinh dang nay de khong pha config admin da nhap san, dong
  thoi them validate field ton tai/writable/dung kieu ma ban cu JS khong lam.

### Commit 3: Frontend goi state/action

- Sua form controller va approval engine dung hai RPC moi.
- Bo cac RPC nho le va logic tinh quyen trong client.
- Giữ UI hien tai de giam rui ro migration.
- Bo han vong lap `watchUI` (`setInterval` 250ms, doc URL param) trong
  `Falinwa.validationProcess.js` — day la co che polling cu, hien dang chay
  song song voi hook `onMounted`/`onRecordSaved` cua
  `Falinwa.formControllerPatch.js` va goi trung `onDocumentChanged`. Sau
  commit nay chi con mot duong goi state duy nhat (qua form controller
  patch), dung `get_approval_state`.
- Co the giu `installInteractionGuard` (chan click capture-phase) nhu lop
  UX chan nham lan trong luc cho RPC tra ve, nhung ro rang day chi la trang
  tri hien thi — quyen quyet dinh that su nam o `execute_approval_action`.

### Commit 4: Owl template

- Tao component/template cho approval bar, info va history.
- Bo HTML string, jQuery mutation va document polling neu khong con can.
- Test lai sau khi form re-render.

### Commit 5: Don dep

- Bo bootstrap khong con su dung.
- Bo method client cu.
- Cap nhat README va tai lieu cau hinh.
- Chay full module regression test.

## 8. Test can viet truoc khi merge

- Khong co process.
- Co process nhung record khong match trigger.
- Tao execution dau tien mot lan duy nhat.
- Khong co rule va co rule active.
- User co quyen va khong co quyen.
- Confirm sang step tiep theo.
- Confirm tai step cuoi.
- Back ve step truoc.
- Restart sau approved/cancelled theo cau hinh.
- Cancel.
- Action/field khong hop le bi tu choi.
- Business action loi thi rollback execution.
- Hai request cung approve mot execution.
- Record moi chua co `res_id`, sau save moi bat dau process.
- Form render lai sau action van hien dung state.

## 9. Ket qua mong doi

Sau refactor, server se la noi duy nhat quyet dinh approval va cap nhat du lieu. Client chi la lop hien thi:

```text
Form open -> get_approval_state -> render
Click     -> execute_approval_action -> get_approval_state -> render
```

Logic moi co the dung cho nhieu business model ma khong can viet lai workflow rieng trong tung form view.