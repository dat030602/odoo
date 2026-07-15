/*
    Tính năng: Báo cáo tổng hợp công nợ nhân viên
    Người tạo: Ngochai
    Ngày tạo: 01/06/2024
*/

-- select * from function_tong_hop_cong_no_nhan_vien('20220101', '20241212', 'sale', 15)
create or replace function function_tong_hop_cong_no_nhan_vien(
     p_date_from timestamp
    , p_date_to timestamp
	, p_account_ids text
    , p_id integer
)
returns table(
	partner_id integer
)
language 'plpgsql'
as $body$
declare
    _p_user_id integer = 0;
begin
    --
    select tar.create_uid into _p_user_id from alpha_report tar where id = p_id;
    -- lấy dữ liệu tài khoản, khách hàng
	drop table if exists tmp_account_account;
    create temporary table tmp_account_account as
    select DISTINCT aml.account_id as account_id
		, aml.partner_id as partner_id, he.id as employee_id, he.code as employee_code
    from account_move_line aml
	left join account_move am on am.id = aml.move_id
	inner join res_partner rp on rp.id = am.partner_id
	inner join res_users ru on rp.id = ru.partner_id
	inner join hr_employee he on he.user_id = ru.id
    where aml.parent_state = 'posted'
		and (p_account_ids = '' or aml.account_id::text= any(string_to_array(p_account_ids, ',')));

	-- tính nợ có đầu kỳ, và phát sinh trong ky
    drop table if exists tmp_balance;
    create temporary table tmp_balance as
    select tcc.account_id as account_id
		, tcc.partner_id as partner_id
		, tcc.employee_id as employee_id
		, tcc.employee_code as employee_code
		, (select sum(aml.debit) as start_debit from account_move_line as aml
			where aml.account_id = tcc.account_id
			and aml.partner_id = tcc.partner_id
			and aml.date < p_date_from
			and aml.parent_state = 'posted'
		  	) as start_debit
		, (select sum(aml.credit) as start_credit from account_move_line as aml
			where aml.account_id = tcc.account_id
			and aml.partner_id = tcc.partner_id
			and aml.date < p_date_from
			and aml.parent_state = 'posted'
		  	) as start_credit
		, (select sum(aml.debit) as debit from account_move_line as aml
			where aml.account_id = tcc.account_id
			and aml.partner_id = tcc.partner_id
			and (p_date_from <= aml.date and aml.date <= p_date_to)
			and aml.parent_state = 'posted'
		  	) as debit
		, (select sum(aml.credit) as credit from account_move_line as aml
			where aml.account_id = tcc.account_id
			and aml.partner_id = tcc.partner_id
			and (p_date_from <= aml.date and aml.date <= p_date_to)
			and aml.parent_state = 'posted'
		  	) as credit
    from tmp_account_account tcc;
	-- tính thêm cuối ky
	drop table if exists tmp_account_move;
    create temporary table tmp_account_move as
	select tb.account_id as account_id
	, tb.partner_id as partner_id
	, tb.employee_id as employee_id
	, tb.employee_code as employee_code
	, CASE
		  WHEN tb.start_debit - tb.start_credit > 0 THEN tb.start_debit - tb.start_credit
		  ELSE 0
	  END AS start_debit
	, CASE
		  WHEN tb.start_credit - tb.start_debit > 0 THEN tb.start_credit - tb.start_debit
		  ELSE 0
	  END AS start_credit
	, tb.debit as debit
	, tb.credit as credit
	, CASE
		  WHEN tb.start_debit is null and tb.start_credit is null and tb.debit -  tb.credit  > 0 THEN tb.debit -  tb.credit
		  WHEN tb.debit is null and tb.credit is null and tb.start_debit -  tb.start_credit  > 0 THEN tb.start_debit -  tb.start_credit
		  WHEN tb.start_debit + tb.debit - tb.start_credit - tb.credit > 0 THEN tb.start_debit + tb.debit - tb.start_credit - tb.credit
		  ELSE 0
	  END AS end_debit
	, CASE
		  WHEN tb.start_debit is null and tb.start_credit is null and tb.credit -  tb.debit  > 0 THEN tb.credit -  tb.debit
		  WHEN tb.debit is null and tb.credit is null and tb.start_credit -  tb.start_debit  > 0 THEN tb.start_credit -  tb.start_debit
		  WHEN tb.start_credit + tb.credit - tb.start_debit - tb.debit > 0 THEN tb.start_credit + tb.credit - tb.start_debit - tb.debit
		  ELSE 0
	  END AS end_credit
	from tmp_balance tb;

	-- Xử lý dữ liệu trên frontend
    delete from alpha_report_line where parent_id = p_id;
    insert into alpha_report_line(
        parent_id, create_uid, write_uid -- bắt buộc
        , account_id, partner_id, employee_id, employee_code
		, start_debit, start_credit, debit, credit, end_debit, end_credit
    )
    select
         p_id , _p_user_id, _p_user_id
        , rs.account_id, rs.partner_id, rs.employee_id, rs.employee_code
        , rs.start_debit, rs.start_credit, rs.debit, rs.credit, rs.end_debit, rs.end_credit
    from tmp_account_move rs;

    -- kết quả trả về
    return query
    select rs.partner_id
    from tmp_account_move rs;
end
$body$;