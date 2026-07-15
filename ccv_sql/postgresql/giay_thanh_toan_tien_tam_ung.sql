/*
    Tính năng: Giấy thanh toan tiền tạm ứng
    Người tạo: Ngochai
    Ngày tạo: 01/06/2024
*/

-- select * from function_giay_thanh_toan_tien_tam_ung('20220101', '20241212', 'sale', 15)
CREATE OR REPLACE FUNCTION public.function_giay_thanh_toan_tien_tam_ung(
	p_date_from timestamp without time zone,
	p_date_to timestamp without time zone,
	p_account_id integer,
	p_partner_id integer,
	p_id integer
)
RETURNS TABLE(account_id integer, partner_id integer)
LANGUAGE 'plpgsql'
COST 100
VOLATILE PARALLEL UNSAFE
ROWS 1000

AS $BODY$
declare
    _p_user_id integer = 0;
begin
    --
    select tar.create_uid into _p_user_id from alpha_report tar where id = p_id;

	-- lấy invoice để tính chi tiết hóa đơn bán ra
    drop table if exists tmp_account_move_line;
    create temporary table tmp_account_move_line as
    select aml.move_id as move_id, aml.partner_id as partner_id
	, aml.account_id as account_dest_id, aml.credit as credit, aml.name as name
	, aml.id as move_line_id
    from account_move_line aml
	left join account_move am on am.id = aml.move_id
    where (p_date_from <= am.invoice_date and am.invoice_date <= p_date_to)
		and aml.parent_state = 'posted'
		and p_account_id = aml.account_id
		and p_partner_id = aml.partner_id
		and aml.credit > 0;

	-- lấy invoice để tính chi tiết hóa đơn bán ra
    drop table if exists tmp_account_move_line2;
    create temporary table tmp_account_move_line2 as
    select rs.move_id as move_id, rs.partner_id as partner_id
	, rs.account_dest_id as account_dest_id, rs.credit as credit,  rs.name as name
	, (select aml.account_id
	   from account_move_line aml
	   where aml.move_id = rs.move_id and aml.id != rs.move_line_id limit 1
    )as account_id
    from tmp_account_move_line rs;

	-- insert dữ liệu phát sinh trong ky
	delete from alpha_report_line5 where parent_id = p_id;
    insert into alpha_report_line5(
        parent_id, create_uid, write_uid -- bắt buộc
        , partner_id
		, move_id
		, account_id, account_dest_id
		, credit
		, note
    )
    select
         p_id , _p_user_id, _p_user_id
        , rs.partner_id
		, rs.move_id
		, rs.account_id, rs.account_dest_id
        , credit
		, rs.name
    from tmp_account_move_line2 rs;

    -- kết quả trả về
    return query
    select p_account_id, rs.partner_id
    from tmp_account_move_line2 rs;
end
$BODY$;