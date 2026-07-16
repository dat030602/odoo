base64 = _dynamic_import('base64')
io = _dynamic_import('io')
xlsxwriter = _dynamic_import('xlsxwriter')
PIL = _dynamic_import('PIL')
image_data_uri = _dynamic_import('odoo').tools.image.image_data_uri
image_process = _dynamic_import('odoo').tools.image.image_process
image_to_base64 = _dynamic_import('odoo').tools.image.image_to_base64
image_data_uri = _dynamic_import('odoo').tools.image.image_data_uri

def get_report_data(rec):
    res = []
    for line in rec.line_ids.with_context(active_test=False):
        l = line.length or 0
        w = line.width or 0
        h = line.height or 0
        carton_meas_str = "{}*{}*{}".format(l, w, h) if (l or w or h) else ""
        product_id = line.with_context(active_test=False).product_id
        image_data = product_id.image_1920 if product_id else False
        picture = {'type': 'image', 'data': image_data} if image_data else ""
        remark_1 = {'type': 'image', 'data': image_data} if image_data else ""
        remark_2 = {'type': 'image', 'data': image_data} if image_data else ""

        res.append({
            'order_name': line.order_ref or "",
            'store_no': "",
            'art_code': "",
            'model': "",
            'description': line.name or "",
            'picture': picture,
            'colour': "",
            'barcode': line.barcode or "",
            'master_barcode': line.x_studio_barcode or "HEHE",
            'pcs_ctn': line.qty_per_carton or 0,
            'nw_pcs': line.product_net_weight or 0.0,
            'carton_meas': 0,
            'v_ctn': line.ctn_cbm or 0.0,
            'gw_ctn': line.gross_weight or 0.0,
            'nw_ctn': line.net_weight or 0.0,
            'qty': line.quantity or 0,
            'ctn': line.carton_quantity or 0,
            'total_v': line.total_cbm or 0.0,
            'total_gw': line.total_gross_weight or 0.0,
            'total_nw': line.total_net_weight or 0.0,
            'remark_1': remark_1,
            'remark_2': remark_2
        })
    return res

def create_format_obj(**kwargs):
    format_dict = {
        'border': 1,
        'align': 'center',
        'valign': 'vcenter',
        'text_wrap': True
    }
    format_dict.update(kwargs)
    return format_dict

def get_format_configs():
    return {
        'default': create_format_obj(),
        'header_normal': create_format_obj(bold=True),
        'header_blue': create_format_obj(bold=True, bg_color='#4A86E8', font_color='black'),
        'header_green': create_format_obj(bold=True, bg_color='#93C47D', font_color='black'),
        'no_border_bold': create_format_obj(border=0, bold=True, align='left')
    }

def setup_column_widths(worksheet):
    col_configs = [
        (0, 0, 5),      # Column 0
        (1, 1, 20),     # Column 1
        (2, 2, 8),      # Column 2
        (3, 4, 14),     # Column 3-4
        (5, 5, 30),     # Column 5
        (6, 6, 15),     # Column 6
        (7, 7, 10),     # Column 7
        (8, 9, 15),     # Column 8-9
        (10, 20, 11),   # Column 10-20
        (21, 22, 20)    # Column 21-22
    ]
    for first_col, last_col, width in col_configs:
        worksheet.set_column(first_col, last_col, width)

def write_excel_cell(worksheet, row, col, cell_value, cell_format):
    if isinstance(cell_value, dict) and cell_value.get('type') == 'image':
        worksheet.write(row, col, "", cell_format)
        b64_data = cell_value.get('data')
        
        if b64_data:
            try:
                image_buffer = io.BytesIO(base64.b64decode(b64_data))
                
                # worksheet.insert_image(row, col, 'image.png', {
                #     'image_data': image_buffer
                # })
                # worksheet.embed_image(row, col, 'image.png', {
                #     'image_data': image_buffer
                # })
            except Exception as e:
                log(f"Conversion Error: {str(e)}")
                worksheet.write(row, col, "", cell_format)

    elif isinstance(cell_value, str) and cell_value.startswith('='):
        worksheet.write_formula(row, col, cell_value, cell_format)
        
    else:
        worksheet.write(row, col, cell_value, cell_format)

def write_merged_cells(worksheet, r1, c1, r2, c2, cell_value, cell_format):
    worksheet.merge_range(r1, c1, r2, c2, "", cell_format)
    write_excel_cell(worksheet, r1, c1, cell_value, cell_format)

def setup_worksheet_print(worksheet):
    worksheet.set_landscape()
    
    worksheet.set_paper(9)
    
    worksheet.fit_to_pages(1, 0)
    
    worksheet.center_horizontally()
    
    worksheet.set_margins(left=0.3, right=0.3, top=0.5, bottom=0.5)

def prepare_formats(workbook):
    workbook_formats = {}
    configs = get_format_configs()
    for format_key, format_properties in configs.items():
        workbook_formats[format_key] = workbook.add_format(format_properties)
    return workbook_formats

def write_header(worksheet, formats, current_row, config):
    if not config:
        return current_row
    worksheet.merge_range(current_row, 0, current_row, 21, config.get('title', ''), formats['no_border_bold'])
    worksheet.set_row(current_row, 30)
    return current_row + 1

def write_body(worksheet, formats, current_row, config):
    if not config:
        return current_row
    worksheet.write(current_row, 0, config.get('info', ''), formats['no_border_bold'])
    return current_row + 1

def write_table(worksheet, formats, current_row, config, data_records):
    if not config:
        return current_row
    
    headers = [
        ("No.", 'header_normal'), 
        ("订单名", 'header_normal'), 
        ("店铺号", 'header_normal'), 
        ("客户型号\nArt. Code", 'header_normal'), 
        ("型号\nModel", 'header_blue'), 
        ("品名\nDescription", 'header_normal'), 
        ("产品图\nPicture", 'header_blue'),
        ("颜色\nColour", 'header_blue'), 
        ("彩盒条码\nBarcode", 'header_normal'), 
        ("外箱条码\nMaster\nBarcode", 'header_normal'), 
        ("每件数量\npcs/ctn", 'header_normal'), 
        ("产品裸重\nkg\nN.W./PCS", 'header_blue'), 
        ("规格\nCarton\nMeas", 'header_green'),
        ("每箱体积\nV/ctn", 'header_green'), 
        ("每件毛重KG\nG.W./ctn", 'header_green'), 
        ("每箱净重KG\nN.W./ctn", 'header_green'), 
        ("数量\nQTY", 'header_green'), 
        ("件数\nCTN", 'header_green'), 
        ("总体积\nTotal\nVol.", 'header_green'),
        ("总毛重\nKG\nTotal\nG.W.", 'header_green'), 
        ("总净重\nKG\nTotal\nN.W.", 'header_green'),
        ("备注\nRemark", 'header_normal'), 
        ("备注\nRemark", 'header_normal')
    ]
    
    for col_num, header_info in enumerate(headers):
        worksheet.write(current_row, col_num, header_info[0], formats[header_info[1]])
    
    worksheet.set_row(current_row, 45)
    current_row += 1

    groups = []
    current_group = []
    current_mb = "" 

    for record in data_records:
        mb = record.get('master_barcode', '')
        if isinstance(mb, str): 
            mb = mb.strip()
        
        if mb and mb == current_mb:
            current_group.append(record)
        else:
            if current_group:
                groups.append(current_group)
            current_group = [record]
            current_mb = mb
            
    if current_group:
        groups.append(current_group)

    item_no = 1
    MASTER_BARCODE_INDEX = 9

    for group in groups:
        group_size = len(group)
        start_row = current_row
        end_row = current_row + group_size - 1
        
        first_rec_mb = group[0].get('master_barcode', '')
        if group_size > 1:
            write_merged_cells(worksheet, start_row, MASTER_BARCODE_INDEX, end_row, MASTER_BARCODE_INDEX, first_rec_mb, formats['default'])
        else:
            write_excel_cell(worksheet, start_row, MASTER_BARCODE_INDEX, first_rec_mb, formats['default'])

        for row_offset, record in enumerate(group):
            actual_row = start_row + row_offset
            worksheet.set_row(actual_row, 60)
            
            row_data = [
                item_no, 
                record.get('order_name', ''), 
                record.get('store_no', ''), 
                record.get('art_code', ''),
                record.get('model', ''), 
                record.get('description', ''), 
                record.get('picture', ''),
                record.get('colour', ''), 
                record.get('barcode', ''), 
                "",
                record.get('pcs_ctn', ''), 
                record.get('nw_pcs', ''), 
                record.get('carton_meas', ''),
                record.get('v_ctn', ''), 
                record.get('gw_ctn', ''), 
                record.get('nw_ctn', ''),
                record.get('qty', ''), 
                record.get('ctn', ''), 
                record.get('total_v', ''),
                record.get('total_gw', ''), 
                record.get('total_nw', ''), 
                record.get('remark_1', ''), 
                record.get('remark_2', '')
            ]
            
            for col_idx, val in enumerate(row_data):
                if col_idx == MASTER_BARCODE_INDEX:
                    continue 
                write_excel_cell(worksheet, actual_row, col_idx, val, formats['default'])
                
            item_no += 1 

        current_row += group_size
        
    return current_row

def write_footer(worksheet, formats, current_row, config):
    if not config:
        return current_row
    current_row += 1
    worksheet.write(current_row, 0, config.get('note', ''), formats['no_border_bold'])
    return current_row + 1

def write_signature(worksheet, formats, current_row, config):
    if not config:
        return current_row
    current_row += 2
    worksheet.write(current_row, 18, config.get('sign', ''), formats['no_border_bold'])
    return current_row + 1

def generate_excel_file(rec):
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet('Order Data')

    setup_worksheet_print(worksheet)
    setup_column_widths(worksheet)

    formats = prepare_formats(workbook)
    data_records = get_report_data(rec)
    
    header_config = None
    body_config = None
    table_config = True
    footer_config = None
    signature_config = None
    
    current_row = 0
    current_row = write_header(worksheet, formats, current_row, header_config)
    current_row = write_body(worksheet, formats, current_row, body_config)
    current_row = write_table(worksheet, formats, current_row, table_config, data_records)
    current_row = write_footer(worksheet, formats, current_row, footer_config)
    current_row = write_signature(worksheet, formats, current_row, signature_config)
    
    workbook.close()
    output.seek(0)
    return output.read()

def execute_download_action(rec):
    excel_data = generate_excel_file(rec)
    excel_base64 = base64.b64encode(excel_data)
    
    current_time_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = "Packing_List_{}_{}.xlsx".format(rec.code, current_time_str)
    
    attachment = env['ir.attachment'].create({
        'name': file_name,
        'type': 'binary',
        'datas': excel_base64,
        'res_model': 'res.users',
        'res_id': env.user.id,
    })
    
    return {
        'type': 'ir.actions.act_url',
        'url': '/web/content/%s?download=true' % attachment.id,
        'target': 'self',
    }

for rec in records:
    action = execute_download_action(rec)