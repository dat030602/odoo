from odoo import api, SUPERUSER_ID

RANK = {
    'model': 10,
    'field': 20,
    'server_action': 30,
    'view': 40,
    'access_right': 50,
    'record_rule': 60,
    'menu': 70,
}


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    Step = env['meta.migration.step']

    # Check if table exists before querying
    cr.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'meta_migration_job'
        );
    """)
    if not cr.fetchone()[0]:
        return

    cr.execute("SELECT * FROM meta_migration_job")
    jobs = cr.dictfetchall()
    for job in jobs:
        if Step.search_count([('job_id', '=', job['id'])]):
            continue

        steps = []

        def add(otype, action='create', **vals):
            steps.append(dict(job_id=job['id'], object_type=otype, action=action, **vals))

        m_type = job.get('migration_type')
        if m_type == 'model_only':
            cr.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'meta_migration_model_line'
                );
            """)
            if cr.fetchone()[0]:
                cr.execute(
                    "SELECT model_name, target_model_name FROM meta_migration_model_line "
                    "WHERE job_id = %s ORDER BY sequence, id",
                    (job['id'],),
                )
                for r in cr.dictfetchall():
                    m_name = (r.get('model_name') or '').strip()
                    tgt_name = (r.get('target_model_name') or '').strip()
                    if m_name:
                        add('model', model_name=m_name, target_model_name=tgt_name)
                        add('field', model_name=m_name, field_name=False)
                        if job.get('copy_access_rights'):
                            add('access_right', model_name=m_name)
                        if job.get('copy_record_rules'):
                            add('record_rule', model_name=m_name)
                        if job.get('create_menu'):
                            add('menu', model_name=m_name)
        elif m_type == 'content':
            # 1. Fields
            cr.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'meta_migration_field_line'
                );
            """)
            if cr.fetchone()[0]:
                cr.execute(
                    "SELECT model_name, field_name FROM meta_migration_field_line "
                    "WHERE job_id = %s ORDER BY id",
                    (job['id'],),
                )
                for r in cr.dictfetchall():
                    if r.get('model_name'):
                        add('field', model_name=r['model_name'].strip(), field_name=(r.get('field_name') or '').strip())

            # 2. Views
            cr.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'meta_migration_view_line'
                );
            """)
            if cr.fetchone()[0]:
                cr.execute(
                    "SELECT model_name FROM meta_migration_view_line "
                    "WHERE job_id = %s ORDER BY id",
                    (job['id'],),
                )
                for r in cr.dictfetchall():
                    m_name = (r.get('model_name') or '').strip()
                    if m_name:
                        if job.get('create_list_view'):
                            add('view', model_name=m_name, view_type='list')
                        if job.get('create_form_view'):
                            add('view', model_name=m_name, view_type='form')
                        if job.get('create_search_view'):
                            add('view', model_name=m_name, view_type='search')

            # 3. Menus
            cr.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'meta_migration_menu_line'
                );
            """)
            if cr.fetchone()[0]:
                cr.execute(
                    "SELECT model_name FROM meta_migration_menu_line "
                    "WHERE job_id = %s ORDER BY id",
                    (job['id'],),
                )
                for r in cr.dictfetchall():
                    m_name = (r.get('model_name') or '').strip()
                    if m_name:
                        add('menu', model_name=m_name)

            # 4. Server actions
            cr.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'meta_migration_action_line'
                );
            """)
            if cr.fetchone()[0]:
                cr.execute(
                    "SELECT xml_id FROM meta_migration_action_line "
                    "WHERE job_id = %s ORDER BY id",
                    (job['id'],),
                )
                for r in cr.dictfetchall():
                    x_id = (r.get('xml_id') or '').strip()
                    if x_id:
                        add('server_action', xml_id=x_id)

        steps.sort(key=lambda v: RANK.get(v['object_type'], 99))
        for n, vals in enumerate(steps, 1):
            Step.create(dict(vals, sequence=n * 10))

        cr.execute("UPDATE meta_migration_job SET stop_on_error = true WHERE id = %s", (job['id'],))
