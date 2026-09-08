# Ke hoach refactor Office Approval Process

> **Cap nhat sau khi doc code hien tai (26/08/2026):** da doc toan bo module
> (`fal_vprocess*.py`, `ir_http.py`, `Falinwa.validationProcess.js`,
> `Falinwa.formControllerPatch.js`, `ir.model.access.csv`, cac view XML). Ket
> qua doi chieu duoc gom o **Muc 10** o cuoi file. Diem quan trong nhat: file
> `ir.model.access.csv` hien dang cho **tat ca user (`base.group_user`) quyen
> `read/write/create/unlink` day du tren ca 4 model** ke ca
> `fal.vprocess.execution` va `fal.vprocess` (cau hinh process). Dieu nay co
> nghia bat ky user noi bo nao cung co the tu ghi `finished=True`,
> `cancelled=False`, doi `step_id`, hoac sua thang cau hinh rule/step ngay tu
> bay gio, bat ke JS lam gi. Day la lo hong bao mat can fix rieng, **doc lap voi
> tien do refactor ORM**, va nen fix truoc/song song voi Phase 1 (xem Muc 10.1).

## 1. Mo ta yeu cau

Module can ho tro quy trinh duyet dong cho nhieu model Odoo:

1. Khi nguoi dung mo form, he thong kiem tra model va record hien tai co can approval hay khong.
2. Neu co approval, he thong xac dinh execution, step hien tai va quyen cua nguoi dung.
3. Form hien cac nut phu hop voi trang thai, step va quyen duyet.
4. Khi nguoi dung bam nut, he thong cap nhat business record va trang thai approval.
5. Sau khi cap nhat, giao dien render lai cac nut va thong tin approval theo trang thai moi.

## 2. Muc tieu kien truc

ORM la nguon quyet dinh duy nhat cho nghiep vu va bao mat. JavaScript chi dam nhan viec goi RPC, hien thi ket qua va render lai template.

Khong de client tu quyet dinh cac noi dung sau:

- Record co match trigger/filter hay khong.
- User co quyen approve hay khong.
- Buoc tiep theo la buoc nao.
- Field nao duoc phep cap nhat.
- Method nao duoc phep goi.
- Execution co con hop le de cap nhat hay da bi nguoi khac xu ly.

## 3. Pham vi giu nguyen

- Cau hinh `fal.vprocess`, `fal.vprocess.step` va `fal.vprocess.rule`.
- Execution `fal.vprocess.execution` lam noi luu trang thai cua record.
- Trigger, process-wide filter va filter cua rule.
- Rule theo user custom, domain hoac server action.
- Cac action confirm, cancel, back va restart.
- Ho tro log message va tao activity neu cau hinh cho phep.
- Cac nut dong trong form approval.

## 4. Phan viec can dua xuong ORM

### 4.1. Lay trang thai approval

Them mot method server-side, vi du:

```text
fal.vprocess.get_state(model_name, record_id)
```

Method nay can:

1. Kiem tra model hop le va record co ton tai.
2. Tim process active phu hop voi model.
3. Kiem tra trigger va process-wide filter bang ORM.
4. Tim execution active cua record/process.
5. Tao execution dau tien neu record vua match trigger.
6. Xac dinh step hien tai, step truoc va step tiep theo.
7. Tinh cac rule dang active theo record.
8. Tinh user hien tai co quyen thao tac hay khong.
9. Tra ve state toi gian cho client, gom trang thai va danh sach nut duoc phep hien.

Ket qua khong nen tra toan bo cau hinh va danh sach user neu client khong can dung.

### 4.2. Xu ly thao tac approval

Them mot method server-side, vi du:

```text
fal.vprocess.execute_action(model_name, record_id, action)
```

Method nay can:

1. Kiem tra lai process, execution, step va quyen cua user.
2. Kiem tra action co hop le voi step hay khong.
3. Kiem tra execution chua bi finished/cancelled va van dung voi record hien tai.
4. Cap nhat business record theo whitelist field/action.
5. Cap nhat execution.
6. Tao message va activity neu can.
7. Tra ve state moi sau khi commit logic.

Toan bo cac buoc tren phai nam trong mot transaction ORM. Khong de client goi truc tiep method tuy y qua chuoi `action_string_*` neu chua duoc whitelist va kiem tra quyen.

## 5. Phan viec con lai o frontend

Frontend van can ton tai vi ORM khong tu chen DOM vao form view.

JavaScript nen duoc rut gon thanh:

1. Hook vao lifecycle mo form va sau khi record save.
2. Goi `get_state(model, record_id)`.
3. Render template approval bar tu state server tra ve.
4. Khoa/mieu ta cac control cua form neu state yeu cau.
5. Khi bam nut, goi `execute_action(...)`.
6. Render lai template tu state moi, khong tu suy dien lai workflow.

Nen thay cach tao HTML bang chuoi va thao tac jQuery phan tan bang mot Owl component/template cua Odoo 19. Component chi nhan state tu ORM lam props.

## 6. Bao mat va tinh dung dan

- Khong tin vao nut bi an tren client; moi action phai duoc authorize lai tren server.
- Kiem tra access rights va record rules cua business model.
- Gioi han model duoc phep xu ly, tranh cho client truyen model tuy y.
- Whitelist cac action method va field co the chay/cap nhat.
- Khong dung `sudo()` cho business update neu khong co ly do nghiep vu ro rang.
- Xem lai ACL cua `fal.vprocess.execution`; user khong nen co quyen ghi tuy y neu workflow server da kiem soat viec ghi.
- Xu ly hai request dong thoi bang row lock hoac kiem tra lai execution trong transaction truoc khi ghi.
- Neu action that bai, khong duoc de execution cap nhat dang do.

## 7. Ke hoach trien khai

### Phase 1: Chuan hoa domain va state

- Tao helper ORM dung chung de tim process, match filter va lay execution.
- Chuyen logic xac dinh step/rule/user tu JavaScript sang Python.
- Viet test cho trigger, filter, rule va cac trang thai execution.

### Phase 2: Chuyen thao tac sang ORM

- Tao method xu ly `confirm`, `cancel`, `back`, `restart`.
- Gom business update, execution update, message va activity vao cung transaction.
- Them kiem tra quyen va whitelist.
- Them co che ngan race condition.

### Phase 3: Rut gon frontend

- Thay cac RPC nho le bang `get_state` va `execute_action`.
- Render approval bar tu state server tra ve.
- Bo logic workflow va update record khoi JavaScript.
- Giữ hook form de refresh state sau khi mo form va sau khi save.

### Phase 4: Chuyen template

- Tao Owl component cho approval bar, info bar va history bar.
- Dung props/state thay cho HTML string va jQuery DOM mutation.
- Dam bao component duoc render lai khi Odoo form re-render.

### Phase 5: Kiem thu va rollout

- Test Python ORM.
- Test access rights voi user duoc phep va khong duoc phep.
- Test hai user approve dong thoi.
- Test record khong match trigger, record moi va record da finished/cancelled.
- Test form desktop/mobile va refresh sau moi action.
- Chi go bo code JavaScript cu sau khi luong moi da pass regression test.

## 8. Tieu chi nghiem thu

- Mo form khong co process: khong co approval UI va khong khoa form.
- Mo form co process nhung khong match trigger: khong hien nut approval.
- Mo form co execution: hien dung step va dung nut theo quyen.
- User khong co quyen khong the thuc hien action bang RPC truc tiep.
- Confirm/cancel/back/restart cap nhat dung business record va execution.
- Action loi thi transaction rollback, khong tao trang thai approval nua voi.
- Sau khi action thanh cong, UI hien ngay state moi ma khong can refresh thu cong.
- Cac business model khac nhau co the dung chung engine ma khong can sua tung form view.

## 9. Ket luan

Co the chuyen phan nghiep vu approval sang ORM gan nhu toan bo. Khong nen dat muc tieu ORM tu render nut, vi viec hien thi van thuoc web client. Kien truc de xuat la:

```text
Form lifecycle -> get_state() -> render template
Button click   -> execute_action() -> get_state() -> render lai
```

Day la huong giup server kiem soat nghiep vu, bao mat va transaction; frontend chi con vai tro hien thi va tuong tac.

## 10. Hien trang code thuc te (doi chieu sau khi doc module)

Phan nay ghi lai chinh xac nhung gi da co trong code, de Muc 4-9 o tren duoc
hieu la "phai lam tiep" chu khong phai "lam tu dau".

### 10.1. ACL dang mo hoan toan cho tat ca user (uu tien cao nhat)

`security/ir.model.access.csv` cho `base.group_user` full CRUD tren ca
`fal.vprocess`, `fal.vprocess.step`, `fal.vprocess.rule` va
`fal.vprocess.execution`. Ket qua:

- Bat ky user nao cung ghi truc tiep `fal.vprocess.execution` (doi
  `step_id`, `finished`, `cancelled`, `previous_step_id`...) ma khong qua
  bat ky check quyen nao — dung nhu client hien dang lam qua
  `createUpdate(s._config.executionModel, item)`.
- Bat ky user nao cung sua duoc chinh cau hinh process/step/rule
  (`fal.vprocess`, `.step`, `.rule`), tuc la tu thay doi ai duoc quyen
  approve.

**Khuyen nghi:** tach ACL thanh 2 nhom ngay ca truoc khi lam Phase 1/2:
- Nhom quan tri (vd nhom moi hoac `base.group_system`): full CRUD tren
  `fal.vprocess`, `.step`, `.rule`.
- User thuong: **chi `perm_read`** tren 4 model nay (can de hien thi info/
  history bar), khong `write/create/unlink` truc tiep. Moi thay doi
  execution phai di qua method server (`sudo()` noi bo, co check quyen
  rieng) chu khong qua ORM write tu client.

### 10.2. Da co mot phan "server-side" nhung theo huong khac voi Muc 4

`models/fal_vprocess.py` da co san:

- `vprocess_models()` — danh sach model dang co process active.
- `vprocess_bootstrap()` — dump toan bo config process/step/rule (khong gom
  user list) ra `session_info` qua `ir_http.py` (`session_info()` override).
- `vp_match(model, res_id, filter_ids)` — evaluate domain cua nhieu
  `ir.filters` bang `search_count`, dung `sudo()`.

`models/fal_vprocess_rule.py` da co `get_allowed_user_ids()` — resolve user
duoc phep theo `user_domain_type` (`custom`/`domain`/`server`), da chay
tren server, an toan hon truoc.

Day la buoc trung gian tot (thay the viec parse domain string trong JS bang
`vp_match`, va thay the viec tinh allowed users trong JS bang
`get_allowed_user_ids`), nhung **huong cua no khac voi Muc 4**: no van dump
toan bo *config* (process/step/rule, action_string, field_string...) ve
client qua `session_info`, roi de JS (`setValidationProcessData`,
`onDocumentChanged`, `createExecutionStep`...) tu doc config do de quyet
dinh step tiep theo, quyen edit/action, va tu ghi truc tiep
`fal.vprocess.execution` + business record. Noi cach khac: domain-matching
va user-resolving da chuyen sang server, nhung **quyet dinh cuoi cung
(state gi, cho phep action gi, ghi gi) van nam o client**.

Khi lam Muc 4.1/4.2, nen coi `vp_match` va `get_allowed_user_ids` la helper
noi bo de tai su dung ben trong `get_state`/`execute_action` (khong viet
lai), nhung **bo dan** co che `vprocess_bootstrap` trong `session_info` +
cache client (`setAllCache`, `_cache.processes/steps/rules`) sau khi
`get_state` da hoat dong on dinh, vi day chinh la phan "client tu suy dien"
ma Muc 2 muon loai bo. Giu lai `vprocess_models()`/session_info chi cho
muc dich hien thi loading overlay ngay tuc thi (frontend biet "model nay
co the co process" de khoa form truoc khi RPC dau tien tra ve), khong dung
no de quyet dinh nghiep vu.

### 10.3. Logic quyet dinh hien dang nam toan bo o JS (`Falinwa.validationProcess.js`, ~2600 dong)

Xac nhan dung nhu Muc 2 mo ta — cu the:

- `onDocumentChanged()`: tu doc cache process/step/rule, tu goi
  `matchDomain` (qua `vp_match`) de quyet dinh co tao execution dau tien
  khong, tu goi `createExecution` (client ghi truc tiep
  `fal.vprocess.execution`), tu tinh step hien tai/next/prev, tu quyet
  dinh khoa edit/action (`_lockEdit`/`_lockActions`) dua tren field cua
  step lay tu cache.
- `checkIfAnyRuleIsActive` / `getActiveRules` / `filterRulesWhereUserIsAuthorized`:
  toan bo o client, chi goi ORM cho tung buoc nho (`vp_match`,
  `get_allowed_user_ids`).
- `createExecutionStep(action, ...)`: day la ham quan trong nhat can
  chuyen thanh `execute_approval_action`. No dang:
  1. Tu tinh `next_step`/`previous_step`/`finished`/`cancelled` o client.
  2. Doc `action_string_confirm/cancel/back/reset` (chuoi ten method,
     phan tach boi dau phay) roi goi `ORM.call(process_model, method, [resId])`
     truc tiep tu browser cho tung method — **khong whitelist server-side**.
  3. Doc `field_string_confirm/cancel/back/reset` (chuoi `field=value,
     field2=value2`, khong ep kieu) roi `write` truc tiep len business
     record qua `createUpdate` — **khong validate field ton tai/writable/
     dung kieu**.
  4. Ghi truc tiep `fal.vprocess.execution` (buoc `item['id'] = s.execution.id`)
     — chi hoat dong duoc vi ACL dang mo (Muc 10.1).
  5. Tu tao message/activity (`createMessage`, `createActivity`,
     `closePreviousActivies`) bang nhieu RPC roi.
  6. Khong co lock/transaction: hai request confirm dong thoi se doc cung
     `s.execution` cache va ghi de len nhau — dung diem rui ro Muc 8/Test da
     liet ke, hien **chua co bat ky co che nao** chan viec nay.

  => Muc 4.2/5.2 (get/execute_action, `transition()`) giai quyet dung
  toan bo nhom nay; khong can sua lai huong, chi can lam.

- Co mot vong lap `setInterval(... , 250ms)` (`watchUI`) doc URL param de
  phat hien doi record/model roi tu goi lai `onDocumentChanged`. Day la co
  che polling, khong phai hook vao lifecycle Odoo that su.

### 10.4. Da co mot lop hook lifecycle moi, nhung dang chay song song voi polling cu

`Falinwa.formControllerPatch.js` (file rieng, da duoc them vao sau) patch
`FormController` de goi `onDocumentChanged` qua `onWillStart` (chi hien
overlay) va `onMounted`/`onRecordSaved` (goi that). Day dung la huong Muc
6.1 mong muon (hook vao lifecycle form thay vi poll).

Van de: file nay **khong thay the** vong lap `watchUI` (setInterval 250ms)
o Muc 10.3 — ca hai co che dang ton tai cung luc trong
`__manifest__.py` (ca hai file JS deu duoc load), nen mot lan doi
model/record co the kich hoat `onDocumentChanged` hai lan (mot lan tu
`formControllerPatch`, mot lan tu vong lap polling khi no phat hien URL
doi). Khi refactor sang `get_approval_state`, nen giu **duy nhat** co che
hook lifecycle (`onMounted`/`onRecordSaved`, co the them `onWillUnmount` de
clear) va bo han `watchUI`/`setInterval`, thay vi giu ca hai.

Co che "interaction guard" (chan click bang capture-phase listener tren
`document`, doc lap voi CSS class) trong `installInteractionGuard` van nen
giu lai **nhu mot lop UX**, nhung phai duoc coi la trang tri (chan nham lan
cho user thay), khong phai bien phap bao mat — bao mat that su phai nam o
`execute_approval_action` (kiem tra quyen tren server truoc khi cho phep
ghi), dung nhu Muc 6 da neu.

### 10.5. Execution model (`fal_vprocess_execution.py`) va Step/Rule config: chua co gi thay doi

Dung nhu Muc 4.2/5 da du kien — hien tai model nay chi co field, **chua co**
method `transition()`, chua co constraint gioi han 1 execution active/cap,
chua co lock. Phan nay giu nguyen ke hoach Muc 5.

`fal.vprocess.step` da co san `back_to_step_id` (+ onchange xoa no khi tat
`buttons_back`) — khop voi field da liet ke trong Muc 4.1, khong can them.

### 10.6. Tac dong den thu tu uu tien Phase

De nghi chen mot **Phase 0** truoc Phase 1 hien tai:

- Phase 0 (ACL): tach quyen nhu Muc 10.1, khong dong den logic nghiep vu.
  Co the lam ngay, rui ro thap, giam ngay lo hong bao mat lon nhat du
  refactor ORM chua xong.
- Phase 1-5: giu nguyen nhu da mo ta, nhung khi cai `get_state`/
  `execute_action`, tan dung lai `vp_match` va `get_allowed_user_ids` thay vi
  viet moi, va nho bo dan `vprocess_bootstrap`/`watchUI` polling khi
  frontend da chuyen hoan toan sang goi `get_state`/`execute_action`
  (Phase 3-4), tranh de 2 nguon state (bootstrap cache vs RPC moi) chay
  song song lau dai.