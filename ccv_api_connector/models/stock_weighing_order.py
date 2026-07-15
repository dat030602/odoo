# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import logging
import traceback
import psycopg2
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

_logger = logging.getLogger(__name__)


class StockWeighingOrder(models.Model):
    _name = 'stock.weighing.order'
    _description = 'Lệnh cân xe'
    _order = 'id desc'

    name = fields.Char('Số lệnh', required=True, copy=False, readonly=True,
                       default=lambda self: self.env['ir.sequence'].next_by_code('stock.weighing.order'))
    sale_id         = fields.Many2one('sale.order',      'Đơn hàng')
    picking_id      = fields.Many2one('stock.picking',   'Phiếu kho')
    partner_id      = fields.Many2one('res.partner',     'Khách hàng')
    product_id      = fields.Many2one('product.product', 'Sản phẩm')
    license_plate   = fields.Char('Biển số xe')
    expected_qty    = fields.Float('SL kế hoạch (tấn)', digits=(16, 3))
    so_phieu    = fields.Char('Số phiếu cân',   default=False)
    tl_lan1     = fields.Float('TL lần 1 (tấn)', digits=(16, 3), default=0.0)
    tl_lan2     = fields.Float('TL lần 2 (tấn)', digits=(16, 3), default=0.0)
    tl_hang     = fields.Float('TL hàng (tấn)',  digits=(16, 3), default=0.0)
    tl_bao_bi   = fields.Float('TL bao bì (tấn)', digits=(16, 3), default=0.0)
    tl_sau_tru_bao_bi = fields.Float('TL sau trừ bao bì (tấn)', digits=(16, 3), default=0.0)
    ngay_can_1  = fields.Datetime('Ngày cân lần 1', default=False)
    ngay_can_2  = fields.Datetime('Ngày cân lần 2', default=False)
    nhan_vien   = fields.Char('Nhân viên cân', default=False)
    nhan_vien_bam_can = fields.Char('Nhân viên bấm cân', default=False)
    is_export   = fields.Boolean('Xuất hàng',  default=False)
    state       = fields.Selection([
        ('draft',   'Chờ cân'),
        ('weighed', 'Đã cân'),
        ('done',    'Hoàn thành'),
    ], default='draft', string='Trạng thái')
    vehicle_line_id = fields.Many2one('sale.vehicle.in.out.line', string="Vehicle Line")
    #odoo_tl_bao_bi  = fields.Float('Odoo TL bao bì (tấn)', related='vehicle_line_id.odoo_tl_bao_bi', readonly=True)

    @api.model
    def _get_weighing_history_correct_name(self, order_id):
        self.env.cr.execute("""
            SELECT v.name correctName
            FROM sale_vehicle_in_out_line v
            LEFT JOIN stock_weighing_order s ON (s.vehicle_line_id = v.id OR v.weighing_order_id = s.id)
            WHERE s.id = %s
        """, (int(order_id),))
        res_query = self.env.cr.fetchall()
        return ":".join([str(r[0]) for r in res_query if r[0]]) if res_query else ""

    @api.model
    def confirm_weigh_result(self, order_id, vals):
        """
        @api.model = class method, gọi được mà không cần record ids.
        Máy cân gọi: args=[order_id, vals], vals có thêm 'req_id' để đối soát.

        ── HỢP ĐỒNG TRẢ VỀ (handshake với máy cân) ─────────────────────────────
        CHỈ khi đã ghi xong record + vehicle_line mới trả:
            {'status': 200, 'code': '1000111', 'req_id': <echo>, 'db': <dbname>,
             'write_date': <thời điểm commit>, 'message': 'Success <id>'}
        Máy cân CHỈ tick OK khi thấy ĐÚNG code '1000111' VÀ đúng req_id nó đã gửi.
        Mọi nhánh lỗi PHẢI trả code khác '1000111' (giữ status 500) — tuyệt đối
        không trả 1000111 ở nhánh chưa ghi đủ, nếu không máy cân sẽ báo OK sai.
        """
        req_id = (vals or {}).get('req_id') or ''
        dbname = self.env.cr.dbname

        # Log ở mức WARNING để hiện kể cả khi odoo chạy log_level=warn
        _logger.warning(
            "[SmartWeight] RECV req_id=%s order_id=%s db=%s vals=%s",
            req_id, order_id, dbname, vals
        )

        try:
            def to_float(v, default=0.0):
                try:
                    return float(v) if v not in (None, '', False) else default
                except:
                    return default

            def format_round_half_up(v):
                if not v:
                    return ""
                try:
                    return f"{Decimal(str(v)).quantize(Decimal('0.001'), rounding=ROUND_HALF_UP):.3f}"
                except:
                    return ""

            def local_to_utc_str(date_str):
                if not date_str:
                    return False
                try:
                    dt = datetime.strptime(str(date_str), '%Y-%m-%d %H:%M:%S')
                    dt_utc = dt - timedelta(hours=7)
                    return dt_utc.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    return date_str

            record = self.browse(int(order_id))
            if not record.exists():
                _logger.warning("[SmartWeight] FAIL req_id=%s order_id=%s — Không tìm thấy lệnh cân", req_id, order_id)
                return {'status': 500, 'code': '500404', 'req_id': req_id, 'db': dbname,
                        'message': 'Không tìm thấy lệnh cân'}

            # ── IDEMPOTENT: nếu phiếu này ĐÃ ghi đúng so_phieu rồi (do retry / đẩy
            #    trùng) thì trả 1000111 luôn, KHÔNG write lại để khỏi nối history trùng.
            so_phieu_in = (vals.get('so_phieu') or '')
            # if record.state == 'weighed' and record.so_phieu and record.so_phieu == so_phieu_in:
            #     _logger.warning(
            #         "[SmartWeight] DUP req_id=%s order_id=%s so_phieu=%s — đã xử lý trước đó, trả 1000111",
            #         req_id, order_id, so_phieu_in
            #     )
            #     return {'status': 200, 'code': '1000111', 'req_id': req_id, 'db': dbname,
            #             'write_date': str(record.write_date), 'message': f'Success {order_id} (dup)'}

            tl_lan1 = to_float(vals.get('tl_lan1') or 0.0)/1000
            tl_lan2 = to_float(vals.get('tl_lan2') or 0.0)/1000
            tl_hang = to_float(vals.get('tl_hang') or 0.0)/1000
            tl_bao_bi = to_float(vals.get('tl_bi') or 0.0)/1000
            tl_sau_tru_bao_bi = round(tl_hang - tl_bao_bi, 3)

            record.write({
                'so_phieu'  : so_phieu_in,
                'tl_lan1'   : tl_lan1,
                'tl_lan2'   : tl_lan2,
                'tl_hang'   : tl_hang,
                'tl_bao_bi' : tl_bao_bi,
                'tl_sau_tru_bao_bi' : tl_sau_tru_bao_bi,
                'ngay_can_1': local_to_utc_str(vals.get('ngay_can_1')),
                'ngay_can_2': local_to_utc_str(vals.get('ngay_can_2')),
                'nhan_vien' : vals.get('nhan_vien') or '',
                'nhan_vien_bam_can' : self.env.user.name,
                'is_export' : bool(vals.get('is_export', False)),
                'state'     : 'weighed',
            })

            if record.vehicle_line_id:
                try:
                    write_vals = {
                        'weighing_so_phieu'  : record.so_phieu,
                        'weighing_tl_lan1'   : format_round_half_up(tl_lan1),
                        'weighing_tl_lan2'   : format_round_half_up(tl_lan2),
                        'weighing_tl_hang'   : format_round_half_up(tl_hang),
                        'weighing_tl_bao_bi' : format_round_half_up(tl_bao_bi),
                        'weighing_tl_sau_tru_bao_bi' : format_round_half_up(tl_sau_tru_bao_bi),
                        'weighing_ngay_can_1': record.ngay_can_1,
                        'weighing_ngay_can_2': record.ngay_can_2,
                        'weighing_nhan_vien' : record.nhan_vien,
                        'weighing_nhan_vien_bam_can': record.nhan_vien_bam_can,
                        'weighing_is_export' : record.is_export,
                    }
                    if record.vehicle_line_id.weighing_order_id:
                        history = record.vehicle_line_id.weighing_history_ids or ""
                        correctName = self._get_weighing_history_correct_name(order_id)
                        # Chống nối history trùng: chỉ thêm nếu order_id chưa nằm trong chuỗi
                        if str(order_id) not in (history or "").split(','):
                            write_vals['weighing_history_ids'] = (
                                f"{history},{order_id},{correctName}" if history else f"{order_id},{correctName}"
                            )

                    record.vehicle_line_id.write(write_vals)

                    # Ép ghi xuống DB để write_date có giá trị thật trước khi trả về.
                    # (Odoo 16: flush_recordset; nếu bản cũ báo lỗi, đổi thành self.env.cr.flush())
                    record.flush_recordset()

                    _logger.warning(
                        "[SmartWeight] DONE req_id=%s order_id=%s code=1000111 db=%s vehicle_line_id=%s write_date=%s",
                        req_id, order_id, dbname, record.vehicle_line_id.id, record.write_date
                    )
                    return {'status': 200, 'code': '1000111', 'req_id': req_id, 'db': dbname,
                            'write_date': str(record.write_date), 'message': f'Success {order_id}'}

                except psycopg2.OperationalError:
                    # Lỗi đua transaction (concurrent update) → để Odoo tự retry, KHÔNG nuốt
                    raise
                except Exception as e:
                    # ★ SỬA QUAN TRỌNG: trước đây nhánh này nuốt lỗi rồi đi tiếp khiến
                    #   data không lên line mà máy cân vẫn nhận OK. Giờ TRẢ 500 rõ ràng.
                    _logger.warning(
                        "[SmartWeight] FAIL req_id=%s order_id=%s — Lỗi cập nhật vehicle_line_id=%s: %s",
                        req_id, order_id, record.vehicle_line_id.id, str(e)
                    )
                    return {'status': 500, 'code': '500300', 'req_id': req_id, 'db': dbname,
                            'message': f'Lỗi cập nhật vehicle_line order_id={order_id}: {e}'}

            # Không có vehicle_line để cập nhật → coi như chưa hoàn tất
            _logger.warning("[SmartWeight] FAIL req_id=%s order_id=%s — không có vehicle_line_id (tl_hang=%.3f)",
                            req_id, order_id, tl_hang)
            return {'status': 500, 'code': '500301', 'req_id': req_id, 'db': dbname,
                    'message': f'Không có vehicle_line cho order_id={order_id}'}

        except psycopg2.OperationalError:
            raise
        except Exception as e:
            _logger.warning("[SmartWeight] FAIL req_id=%s order_id=%s — LỖI: %s\n%s",
                            req_id, order_id, str(e), traceback.format_exc())
            return {'status': 500, 'code': '500500', 'req_id': req_id, 'db': dbname,
                    'message': f"order_id={order_id} Final Error: {str(e)}"}
