/*
    Tính năng: Biên bản kiểm kê vật tư hàng hóa
    Người tạo: Ngochai
    Ngày tạo: 01/06/2024
*/

-- select * from function_bien_ban_kiem_ke_vat_tu_hang_hoa('20220101', '20241212', 'sale', 15)
create or replace function function_bien_ban_kiem_ke_vat_tu_hang_hoa(
    p_id integer
)
returns table(
	id integer
)
language 'plpgsql'
as $body$
declare
    _p_user_id integer = 0;
begin
    --
    select tar.create_uid into _p_user_id from alpha_report tar where tar.id = p_id;

	-- tính cuối ky
	drop table if exists tml_bien_ban_kiem_ke_hang_hoa_vat_tu;
    create temporary table tml_bien_ban_kiem_ke_hang_hoa_vat_tu as
	select pp.default_code as default_code
	, pp.id as product_id
	, pt.uom_id as uom_id
	, sq.quantity as quantity
	, sq.inventory_quantity as inventory_quantity
	, sq.inventory_diff_quantity as diff_quantity
	from stock_quant sq
	left join product_product pp on pp.id = sq.product_id
	left join product_template pt on pt.id = pp.product_tmpl_id
    where sq.inventory_quantity > 0;

	-- Xử lý dữ liệu trên frontend
    delete from alpha_report_line where parent_id = p_id;
    insert into alpha_report_line(
        parent_id, create_uid, write_uid -- bắt buộc
        , default_code
        , product_id
        , uom_id
		, quantity
		, inventory_quantity
		, diff_quantity
    )
    select
         p_id , _p_user_id, _p_user_id
        , rs.default_code
        , rs.product_id
        , rs.uom_id
		, rs.quantity
		, rs.inventory_quantity
		, rs.diff_quantity
    from tml_bien_ban_kiem_ke_hang_hoa_vat_tu rs;

    -- kết quả trả về
    return query
    select rs.product_id
    from tml_bien_ban_kiem_ke_hang_hoa_vat_tu rs;
end
$body$;