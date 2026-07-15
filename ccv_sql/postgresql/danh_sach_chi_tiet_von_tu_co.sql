/*
    Tính năng: Danh sách chi tiết vốn tự có
    Người tạo: Ngochai
    Ngày tạo: 01/06/2024
*/

-- select * from function_danh_sach_chi_tiet_von_tu_co('20241212', 'sale', 15)
create or replace function function_danh_sach_chi_tiet_von_tu_co(
    p_date_to timestamp
	, p_account_ids text
    , p_id integer
)
returns table(
	account_id integer
)
language 'plpgsql'
as $body$
declare
    _p_user_id integer = 0;
begin
    --
    select tar.create_uid into _p_user_id from alpha_report tar where id = p_id;

	-- tính phat sinh trong ngày
	drop table if exists tml_danh_sach_chi_tiet_von_tu_co;
    create temporary table tml_danh_sach_chi_tiet_von_tu_co as
	select am.id as move_id
	, aml.account_id as account_id
	, am.partner_id as partner_id
    , aml.date as date
    , aml.name as note
    , aml.debit as amount
	from account_move_line aml
	left join account_move am on am.id = aml.move_id
    where aml.parent_state = 'posted'
		and aml.date = p_date_to
		and aml.account_id::text= any(string_to_array(p_account_ids, ','));

	-- Xử lý dữ liệu trên frontend
    delete from alpha_report_line7 where parent_id = p_id;
    insert into alpha_report_line7(
        parent_id, create_uid, write_uid -- bắt buộc
        , move_id
        , account_id
        , invoice_date
        , date
        , note
        , amount
        , partner_id
    )
    select
         p_id , _p_user_id, _p_user_id
        , rs.move_id
        , rs.account_id
        , rs.date
        , rs.date
        , rs.note
        , rs.amount
        , rs.partner_id
    from tml_danh_sach_chi_tiet_von_tu_co rs;

    -- kết quả trả về
    return query
    select rs.account_id
    from tml_danh_sach_chi_tiet_von_tu_co rs;
end
$body$;