from odoo import models, fields
import io
try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None

class AccountReport(models.Model):
    _inherit = 'account.report'

    ##################
    # Filter tiền tệ #
    ##################

    filter_currency = fields.Boolean(
        string="Currencies",
        compute=lambda x: x._compute_report_option_filter('filter_currency', True),
        readonly=False,
        store=True,
        depends=['root_report_id'],
    )
    def _init_options_currency(self, options, previous_options=None):
        if not self.filter_currency:
            return
        # Fetch only active currencies
        currencies = self.env['res.currency'].search([])
        # Find VND currency
        vnd_currency = self.env['res.currency'].search([('name', '=', 'VND')], limit=1)
        
        options['currency_options'] = []
        for currency in currencies:
            # Set VND as selected by default
            is_selected = currency.id == vnd_currency.id if vnd_currency else False
            options['currency_options'].append({
                'id': currency.id, 
                'name': currency.name, 
                'selected': is_selected
            })
        
        if previous_options and previous_options.get('currency_options'):
            previously_selected_ids = [x['id'] for x in previous_options['currency_options'] if x.get('selected')]
            for opt in options['currency_options']:
                opt['selected'] = opt['id'] in previously_selected_ids

    def _identify_currency_indices(self, options):
        """Identify currency column indices"""
        monetary_columns = []
        currency_columns = []
        foreign_currency_columns = []
        
        for col_index, column_option in enumerate(options["columns"]):
            if column_option.get("figure_type") == "monetary":
                monetary_columns.append(col_index)
                
                expression_label = column_option.get("expression_label")
                if expression_label == 'foreign_balance':
                    foreign_currency_columns.append(col_index)
                elif expression_label != 'amount_currency':  # Exclude amount_currency columns
                    currency_columns.append(col_index)
                    
        return monetary_columns, currency_columns, foreign_currency_columns

    def _get_selected_currency(self, options, company_currency, currency_env):
        """Get selected currencies from options"""
        currency = company_currency
        if options.get('currency_options'):
            selected_ids = [c['id'] for c in options['currency_options'] if c.get('selected')]
            if selected_ids:
                currency = currency_env.browse(selected_ids[0])

        foreign_currency = company_currency
        if options.get('currency_nt_options'):
            selected_ids = [c['id'] for c in options['currency_nt_options'] if c.get('selected')]
            if selected_ids:
                foreign_currency = currency_env.browse(selected_ids[0])

        return currency, foreign_currency

    def _apply_conversion(self, column_obj, currency, value):
        """Format currency value - unified function"""
        if isinstance(value, dict):
            # Handle column object case
            no_format_value = float(value['no_format']) if isinstance(value['no_format'], (int, float)) else 0.0
        else:
            # Handle direct value case
            no_format_value = float(value) if isinstance(value, (int, float)) else 0.0
            
        if self._context.get("print_mode") and self._context.get("export_to_xlsx_partner"):
            column_obj.update({
                "name": no_format_value,  # Export to xlsx as float for sum
                "no_format": no_format_value
            })
        else:
            column_obj.update({
                "name": currency.format(no_format_value),
                "no_format": no_format_value
            })
        return column_obj

    def export_to_xlsx(self, options, response=None):
        if not xlsxwriter:
            return super().export_to_xlsx(options, response)
            
        if self.custom_handler_model_name == 'account.partner.ledger.report.handler': #áp dụng với bản in xlsx account.partner.ledger.report.handler
            self = self.with_context(export_to_xlsx_partner=True)
            def write_with_colspan(sheet, x, y, value, colspan, style):
                if colspan == 1:
                    sheet.write(y, x, value, style)
                else:
                    sheet.merge_range(y, x, y, x + colspan - 1, value, style)
            self.ensure_one()
            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output, {
                'in_memory': True,
                'strings_to_formulas': False,
            })
            sheet = workbook.add_worksheet(self.name[:31])

            date_default_col1_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666', 'indent': 2, 'num_format': 'yyyy-mm-dd'})
            date_default_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666', 'num_format': 'yyyy-mm-dd'})
            default_col1_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666', 'indent': 2})
            default_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666'})
            title_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2})
            level_0_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 13, 'bottom': 6, 'font_color': '#666666'})
            level_1_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 13, 'bottom': 1, 'font_color': '#666666'})
            level_2_col1_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 12, 'font_color': '#666666', 'indent': 1})
            level_2_col1_total_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 12, 'font_color': '#666666'})
            level_2_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 12, 'font_color': '#666666'})
            level_3_col1_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666', 'indent': 2})
            level_3_col1_total_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 12, 'font_color': '#666666', 'indent': 1})
            level_3_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666'})

            #Set the first column width to 50
            sheet.set_column(0, 0, 50)

            y_offset = 0
            x_offset = 1 # 1 and not 0 to leave space for the line name
            print_mode_self = self.with_context(no_format=True, print_mode=True, prefetch_fields=False)
            print_options = print_mode_self._get_options(previous_options=options)
            lines = self._filter_out_folded_children(print_mode_self._get_lines(print_options))

            # Add headers.
            # For this, iterate in the same way as done in main_table_header template
            column_headers_render_data = self._get_column_headers_render_data(print_options)
            for header_level_index, header_level in enumerate(print_options['column_headers']):
                for header_to_render in header_level * column_headers_render_data['level_repetitions'][header_level_index]:
                    colspan = header_to_render.get('colspan', column_headers_render_data['level_colspan'][header_level_index])
                    write_with_colspan(sheet, x_offset, y_offset, header_to_render.get('name', ''), colspan, title_style)
                    x_offset += colspan
                if print_options['show_growth_comparison']:
                    write_with_colspan(sheet, x_offset, y_offset, '%', 1, title_style)
                y_offset += 1
                x_offset = 1

            for subheader in column_headers_render_data['custom_subheaders']:
                colspan = subheader.get('colspan', 1)
                write_with_colspan(sheet, x_offset, y_offset, subheader.get('name', ''), colspan, title_style)
                x_offset += colspan
            y_offset += 1
            x_offset = 1

            for column in print_options['columns']:
                colspan = column.get('colspan', 1)
                write_with_colspan(sheet, x_offset, y_offset, column.get('name', ''), colspan, title_style)
                x_offset += colspan
            y_offset += 1

            if print_options.get('order_column'):
                lines = self._sort_lines(lines, print_options)

            # Add lines.
            for y in range(0, len(lines)):
                level = lines[y].get('level')
                if lines[y].get('caret_options'):
                    style = level_3_style
                    col1_style = level_3_col1_style
                elif level == 0:
                    y_offset += 1
                    style = level_0_style
                    col1_style = style
                elif level == 1:
                    style = level_1_style
                    col1_style = style
                elif level == 2:
                    style = level_2_style
                    col1_style = 'total' in lines[y].get('class', '').split(' ') and level_2_col1_total_style or level_2_col1_style
                elif level == 3:
                    style = level_3_style
                    col1_style = 'total' in lines[y].get('class', '').split(' ') and level_3_col1_total_style or level_3_col1_style
                else:
                    style = default_style
                    col1_style = default_col1_style

                #write the first column, with a specific style to manage the indentation
                cell_type, cell_value = self._get_cell_type_value(lines[y])
                if cell_type == 'date':
                    sheet.write_datetime(y + y_offset, 0, cell_value, date_default_col1_style)
                else:
                    sheet.write(y + y_offset, 0, cell_value, col1_style)

                #write all the remaining cells
                columns = lines[y]['columns']
                if print_options['show_growth_comparison'] and 'growth_comparison_data' in lines[y]:
                    columns += [lines[y].get('growth_comparison_data')]
                for x, column in enumerate(columns, start=1):
                    cell_type, cell_value = self._get_cell_type_value(column)

                    if cell_type == 'date':
                        sheet.write_datetime(y + y_offset, x + lines[y].get('colspan', 1) - 1, cell_value, date_default_style)
                    else:
                        if isinstance(cell_value, (int, float)):
                            if isinstance(cell_value, int) or cell_value.is_integer():
                                style_integer = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666', 'num_format': '#,##0', 'bold': True})
                                if level == 1:
                                    style_integer = workbook.add_format({'font_name': 'Arial', 'font_size': 13, 'font_color': '#666666', 'num_format': '#,##0', 'bold': True})
                                sheet.write(y + y_offset, x + lines[y].get('colspan', 1) - 1, cell_value, style_integer)
                            else:
                                style_float = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666', 'num_format': '#,##0.00', 'bold': True})
                                if level == 1:
                                    style_float = workbook.add_format({'font_name': 'Arial', 'font_size': 13, 'font_color': '#666666', 'num_format': '#,##0.00', 'bold': True})
                                sheet.write(y + y_offset, x + lines[y].get('colspan', 1) - 1, cell_value, style_float)
                        else:
                            sheet.write(y + y_offset, x + lines[y].get('colspan', 1) - 1, cell_value, style)

            workbook.close()
            output.seek(0)
            generated_file = output.read()
            output.close()

            return {
                'file_name': self.get_default_report_filename('xlsx'),
                'file_content': generated_file,
                'file_type': 'xlsx',
            }
        else:
            return super().export_to_xlsx(options, response)

    def _process_line(self, currency_columns, foreign_currency_columns, selected_currency, selected_foreign_currency, columns):
        """Format currency columns for a line"""
        updated_columns = []
        
        for col_index, column in enumerate(columns):
            column_obj = {
                'name': column.get('name', ''), 
                'no_format': column.get('no_format', ''), 
                'class': column.get('class', '')
            }

            if col_index in currency_columns and column.get('no_format') is not None:
                updated_columns.append(self._apply_conversion(column_obj, selected_currency, column))
            elif col_index in foreign_currency_columns and column.get('no_format') is not None:
                updated_columns.append(self._apply_conversion(column_obj, selected_foreign_currency, column))
            else:
                updated_columns.append(column_obj)

        return updated_columns

    def _get_lines(self, options, all_column_groups_expression_totals=None):
        """Format currency columns"""
        self.ensure_one()
        lines = super()._get_lines(options, all_column_groups_expression_totals)
        
        # Get currency settings
        currency_env = self.env['res.currency']
        company_currency = self.env.company.currency_id
        selected_currency, selected_foreign_currency = self._get_selected_currency(options, company_currency, currency_env)
        monetary_columns, currency_columns, foreign_currency_columns = self._identify_currency_indices(options)

        if not (currency_columns or foreign_currency_columns):
            return lines

        # Format currency columns for all lines
        for line in lines:
            columns = line['columns']
            if not any(
                idx < len(columns) and columns[idx].get('no_format') is not None
                for idx in monetary_columns
            ):
                continue
                
            line['columns'] = self._process_line(
                currency_columns, foreign_currency_columns, selected_currency, selected_foreign_currency, columns
            )

        return lines

    #########################
    # Filter số dư ngoại tệ #
    #########################

    filter_currency_nt = fields.Boolean(
        string="Currencies NT",
        compute=lambda x: x._compute_report_option_filter('filter_currency_nt', True),
        readonly=False,
        store=True,
        depends=['root_report_id'],
    )

    def _init_options_currency_nt(self, options, previous_options=None):
        if not self.filter_currency_nt:
            return
        currencies = self.env['res.currency'].search([])
        currency_nt_options = [{'id': 2, 'name': "USD", 'selected': True}]
        currency_nt_options += [{'id': currency.id, 'name': currency.name, 'selected': False} for currency in currencies if currency.id != 2]
        options['currency_nt_options'] = currency_nt_options

        if previous_options and previous_options.get('currency_nt_options'):
            previously_selected_ids = [x['id'] for x in previous_options['currency_nt_options'] if x.get('selected')]
            for opt in options['currency_nt_options']:
                opt['selected'] = opt['id'] in previously_selected_ids
