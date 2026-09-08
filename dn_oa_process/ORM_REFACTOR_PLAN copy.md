
def _get_approval_history(rec, execution_id):
    """
    Get approval history from execution record.
    Based on JavaScript getActiveExecution() logic.
    
    Returns list of dicts with: date, user_id, user_name, step_id, step_name, action, is_approve, is_cancel
    """
    execution = env['fal.vprocess.execution'].browse(execution_id)
    if not execution.exists():
        raise UserError("Execution does not exist!")

    history = []

    # Get messages related to execution (same as JS: execution.message_ids)
    messages = env['mail.message'].search([
        ('id', 'in', execution.message_ids.ids)
    ], order='id asc')

    # Get tracking values (same as JS: mail.tracking.value)
    trackings = env['mail.tracking.value'].search([
        ('mail_message_id', 'in', messages.ids)
    ], order='id asc')

    # Get field metadata to identify step_id, finished, cancelled fields
    # Same as JS: ir.model.data lookup
    track_fields = env['ir.model.data'].search([
        ('name', 'in', [
            'field_fal_vprocess_execution__step_id',
            'field_fal_vprocess_execution__finished',
            'field_fal_vprocess_execution__cancelled'
        ])
    ])

    # Build field ID mapping (same as JS loop)
    step_id_field = 0
    finish_field = 0
    cancel_field = 0

    for tf in track_fields:
        if tf.name == 'field_fal_vprocess_execution__step_id':
            step_id_field = tf.res_id
        elif tf.name == 'field_fal_vprocess_execution__finished':
            finish_field = tf.res_id
        elif tf.name == 'field_fal_vprocess_execution__cancelled':
            cancel_field = tf.res_id

    # Process each tracking record (same logic as JS map function)
    for track in trackings:
        field_id = track.field_id.id if track.field_id else 0

        action = None
        is_approve = False
        is_cancel = False
        step_id = None
        step_name = None

        # Check if this tracking is for step_id field
        if field_id == step_id_field:
            # FIX: use old_value_integer (step that was just approved),
            # not new_value_integer (step execution moved TO)
            if track.old_value_integer:
                step = env['fal.vprocess.step'].browse(track.old_value_integer)
                if step.exists():
                    step_id = step.id
                    step_name = step.name
                else:
                    step_name = 'Step 0'
            else:
                # No previous step recorded → was on the very first step
                step_id = None
                step_name = 'Step 0'
            action = 'step_change'

        # Check if this tracking is for finished field (approve)
        elif field_id == finish_field:
            if track.new_value_integer == 1:
                is_approve = True
                action = 'approve'

        # Check if this tracking is for cancelled field (cancel)
        elif field_id == cancel_field:
            if track.new_value_integer == 1:
                is_cancel = True
                action = 'cancel'

        # Only add to history if we have a valid action
        if action:
            # Get related message to extract author and timestamp
            message = track.mail_message_id.sudo()
            author_id = message.author_id.sudo()
            author_user_id = author_id.main_user_id.sudo()
            author_employee_id = author_user_id.employee_ids.sudo()[0] if author_user_id.employee_ids.sudo() else author_user_id.employee_ids
            author_name = message.author_id.name if message.author_id else 'Unknown'
            write_date = message.write_date

            # Apply timezone offset (+8 hours, same as JS)
            if write_date:
                write_date = write_date + datetime.timedelta(hours=8)

            vals = {
                'raw_date': write_date,
                'date': write_date.strftime('%Y-%m-%d %H:%M:%S') if write_date else '',
                'author_employee_id': author_employee_id.id if author_employee_id else None,
                'author_employee_name': author_employee_id.name if author_employee_id else None,
                'job_position_id': author_employee_id.job_id.id if author_employee_id and author_employee_id.job_id else None,
                'job_position_name': author_employee_id.job_id.name if author_employee_id and author_employee_id.job_id else None,
                'user_id': author_user_id.id,
                'user_name': author_name,
                'step_id': step_id,
                'step_name': step_name,
                'action': action,
                'is_approve': is_approve,
                'is_cancel': is_cancel,
            }

            if env.context.get('sign', False):
                vals['signature'] = author_user_id.sudo().x_studio_approval_signature if author_user_id else None

            history.append(vals)
    
    history.sort(key=lambda x: x['raw_date'] or datetime.datetime.min)

    last_cancel_idx = -1
    last_step0_idx = -1
    
    for i in range(len(history) - 1, -1, -1):
        action = history[i].get('action')
        step_name = history[i].get('step_name') or ''
        
        if last_cancel_idx == -1 and action == 'cancel':
            last_cancel_idx = i
            
        if last_step0_idx == -1 and 'Step 0' in step_name:
            last_step0_idx = i
            
        if last_cancel_idx != -1 and last_step0_idx != -1:
            break

    if last_cancel_idx != -1:
        if last_step0_idx > last_cancel_idx:
            history = history[last_step0_idx:]
            
        elif last_cancel_idx < len(history) - 1:
            history = history[last_cancel_idx + 1:]

    return history

active_model = env.context.get('active_model')
active_id = env.context.get('active_id')
execution_id = env.context.get('execution_id')

if active_model and active_id and execution_id:
    record = env[active_model].browse(active_id)
    action = _get_approval_history(record, execution_id)
def _generate_html(rec, execution_id):
    if not execution_id:
        return ""
    
    histories = env.ref('mb.base_get_approved').sudo().with_context(
        active_model=rec._name,
        active_id=rec.id,
        active_ids=rec.ids,
        execution_id=execution_id
    ).run()
    
    if not histories:
        return ""
    # Badge style mapping by action
    badge_map = {
        'approve':     ('success', 'Approved'),
        'cancel':      ('danger',  'Cancelled'),
        'step_change': ('success', 'Approved'),
        # 'step_change': ('info',    'Step Changed'),
    }
    # Solid background + white text for high contrast readability
    badge_colors = {
        'success':   ('#ffffff', '#28a745'),
        'danger':    ('#ffffff', '#dc3545'),
        'info':      ('#ffffff', '#17a2b8'),
        'secondary': ('#ffffff', '#6c757d'),
    }
    # Common cell style: dark text for readability
    cell_style = 'padding:7px 10px;color:#212529;'
    # Table header
    rows = """
        <table style="width:100%;border-collapse:collapse;font-size:13px;font-family:sans-serif;color:#212529;">
            <thead>
                <tr style="background:#e9ecef;border-bottom:2px solid #ced4da;">
                    <th class="fw-bold" style="padding:8px 10px;text-align:center;width:50px;color:#212529;">No.</th>
                    <th class="fw-bold" style="padding:8px 10px;text-align:left;color:#212529;">Date</th>
                    <th class="fw-bold" style="padding:8px 10px;text-align:left;color:#212529;">Approver</th>
                    <th class="fw-bold" style="padding:8px 10px;text-align:left;color:#212529;">Job Position</th>
                    <th class="fw-bold" style="padding:8px 10px;text-align:center;color:#212529;">Status</th>
                </tr>
            </thead>
            <tbody>
    """
    for idx, h in enumerate(histories, start=1):
        action = h.get('action') or ''
        log(action)
        badge_class, badge_label = badge_map.get(action, ('secondary', action.replace('_', ' ').title()))
        text_color, bg_color = badge_colors.get(badge_class, ('#ffffff', '#6c757d'))
        badge_html = (
            f'<span style="'
            f'display:inline-block;padding:3px 10px;border-radius:10px;'
            f'background-color:{bg_color};color:{text_color};'
            f'font-size:11px;font-weight:600;white-space:nowrap;">'
            f'{badge_label}</span>'
        )
        # Alternate row background
        row_bg = '#ffffff' if idx % 2 == 1 else '#f8f9fa'
        rows += f"""
                <tr style="background:{row_bg};border-bottom:1px solid #dee2e6;">
                    <td style="{cell_style}text-align:center;">{idx}</td>
                    <td style="{cell_style}">{h.get('date') or ''}</td>
                    <td style="{cell_style}">{h.get('user_name') or ''}</td>
                    <td style="{cell_style}">{h.get('job_position_name') or ''}</td>
                    <td style="{cell_style}text-align:center;">{badge_html}</td>
                </tr>
        """
    rows += """
            </tbody>
        </table>
    """
    return rows
active_model = env.context.get('active_model')
active_id = env.context.get('active_id')
record = env[active_model].browse(active_id)
execution = env['fal.vprocess.execution'].search([
    ('process_model', '=', active_model),
    ('target', '=', active_id)
], limit=1)
action = _generate_html(record, execution.id)

đây là code tôi làm cho khách hàng làm field html, bạn hãy viết thành code python và js
build một theme xem lịch sử bằng field html cho read only trong wizard
nút history sẽ call cái này, nhưng tôi đang build theo message thread, hãy chỉnh lại cho theo model history mới
nút history sẽ để cuối cùng, không để trên đầu button box