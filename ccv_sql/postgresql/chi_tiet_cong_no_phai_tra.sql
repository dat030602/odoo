/*
    Tính năng: Chi tiết công nợ phải trả
    Người tạo: Ngochai
    Ngày tạo: 01/06/2024
*/

-- select * from function_chi_tiet_cong_no_phai_tra('20220101', '20241212', 'sale', 15)
CREATE OR REPLACE FUNCTION public.function_chi_tiet_cong_no_phai_tra(
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
    -- lấy dữ liệu tài khoản, khách hàng
    drop table if exists tmp_account_account;
    create temporary table tmp_account_account as
    select DISTINCT aml.account_id as account_id
        , aml.partner_id as partner_id
    from account_move_line aml
    left join account_move am on am.id = aml.move_id
    where aml.parent_state = 'posted'
        and p_account_id = aml.account_id
        and p_partner_id = aml.partner_id;

    -- tính nợ có đầu kỳ
    drop table if exists tmp_dau_ky;
    create temporary table tmp_dau_ky as
    select tcc.account_id as account_id
        , tcc.partner_id as partner_id
        , (select sum(aml.debit) as start_debit from account_move_line as aml
            where aml.account_id = tcc.account_id
            and aml.partner_id = tcc.partner_id
            and aml.date < p_date_from
            and aml.parent_state = 'posted'
            ) as end_debit
        , (select sum(aml.credit) as start_credit from account_move_line as aml
            where aml.account_id = tcc.account_id
            and aml.partner_id = tcc.partner_id
            and aml.date < p_date_from
            and aml.parent_state = 'posted'
            ) as end_credit
    from tmp_account_account tcc;

    -- Insert dau ky truoc
    delete from alpha_report_line2 where parent_id = p_id;
    insert into alpha_report_line2(
        parent_id, create_uid, write_uid -- bắt buộc
        , note, partner_id, account_id
        , end_debit, end_credit
    )
    select
         p_id , _p_user_id, _p_user_id
        , 'Số dư đầu kỳ', rs.partner_id, p_account_id
        , CASE
          WHEN rs.end_debit - rs.end_credit > 0 THEN rs.end_debit - rs.end_credit
          ELSE 0
          END AS end_debit
        , CASE
          WHEN rs.end_credit - rs.end_debit > 0 THEN rs.end_credit - rs.end_debit
          ELSE 0
          END AS end_credit
    from tmp_dau_ky rs;

	-- lay hoa đơn đầu vào
	drop table if exists tmp_account;
    create temporary table tmp_account as
	select DISTINCT am.id as move_id
	from account_move_line aml
	left join account_move am on aml.move_id = am.id
	where aml.partner_id = p_partner_id
	and aml.account_id = p_account_id
	and am.state = 'posted' and am.move_type = 'in_invoice'
	and(p_date_from <= am.invoice_date and am.invoice_date <= p_date_to);

	-- lay bang 1 move line ben hoa don
	drop table if exists tmp_one;
    create temporary table tmp_one as
	select aml.id as line_id, ta.move_id as move_id
	from account_move_line aml
	inner join tmp_account ta on aml.move_id = ta.move_id
	where p_account_id != aml.account_id;

	-- lay bang 2 move line ben thanh toán
	drop table if exists tmp_two;
    create temporary table tmp_two as
	select apr.debit_move_id as line_id, ta.move_id as move_id
	from account_move_line aml
	inner join tmp_account ta on aml.move_id = ta.move_id
	left join account_partial_reconcile apr on apr.credit_move_id = aml.id;

	-- gộp 2 bảng lại
	drop table if exists tmp_one_two;
    create temporary table tmp_one_two as
	SELECT line_id as line_id, move_id as move_id FROM tmp_one
	UNION
	SELECT  line_id as line_id, move_id as move_id FROM tmp_two;

	-- lấy luôn các khoản trả trước không gắn vô hóa don
	drop table if exists tmp_account_move_for_payment;
    create temporary table tmp_account_move_for_payment as
	select DISTINCT am.id as move_id
	from account_move_line aml
	left join account_move am on aml.move_id = am.id
	left outer join tmp_two tt on aml.id = tt.line_id
	where aml.partner_id = p_partner_id
	and tt.line_id is null
	and aml.account_id = p_account_id
	and am.state = 'posted' and am.move_type = 'entry'
	and am.payment_id is not null
	and(p_date_from <= am.date and am.date <= p_date_to);

	drop table if exists tmp_three;
    create temporary table tmp_three as
	select aml.id as line_id, ta.move_id as move_id
	from account_move_line aml
	inner join tmp_account_move_for_payment ta on aml.move_id = ta.move_id
	where p_account_id != aml.account_id;

	-- gộp 2 bảng lại
	drop table if exists tmp_account_move_line;
    create temporary table tmp_account_move_line as
	SELECT line_id as line_id, move_id as move_id FROM tmp_one_two
	UNION
	SELECT  line_id as line_id, move_id as move_id FROM tmp_three;

    -- lấy invoice để tính chi tiết hóa đơn bán ra
    drop table if exists tmp_account_account2;
    create temporary table tmp_account_account2 as
    select DISTINCT aml.move_id as move_id
    from account_move_line aml
    inner join tmp_account_move_line tal on tal.line_id = aml.id;

    -- Tính chi tiết hóa đơn bán ra trong ky
    drop table if exists tmp_phat_sinh_trong_ky;
    create temporary table tmp_phat_sinh_trong_ky as
    select
        aml.partner_id as partner_id
        , rp.code_contact as partner_code
        , aml.date as date
        , aml.move_id as move_id
        , am.ref as reference
        , aml.quantity as product_uom_qty
        , aml.price_unit as price_unit
        , aml.name as note
        , aml.account_id as account_dest_id
		, case
			  when am.currency_id != 23 and aml.debit > 0 then aml.amount_currency
			  else aml.debit
		  end as debit
        , case
			  when am.currency_id != 23 and aml.credit > 0 and am.payment_id is not null then - aml.amount_currency
			  else aml.credit
		  end as credit
        , aml.product_uom_id as uom_id

    from account_move_line aml
	left join account_move am on am.id = aml.move_id
    inner join tmp_account_account2 taa on taa.move_id = am.id
    left join res_partner rp on rp.id = aml.partner_id
    where p_account_id != aml.account_id
		and p_partner_id = aml.partner_id
		and am.state = 'posted'
	ORDER BY case
				when am.invoice_date is not null then am.invoice_date
			  	else am.date
		  	 end, taa.move_id;

    -- insert dữ liệu phát sinh trong ky
    insert into alpha_report_line2(
        parent_id, create_uid, write_uid -- bắt buộc
        , partner_id, date, partner_code
        , move_id, reference, note
        , account_id, account_dest_id
        , debit, credit
        , product_uom_qty, price_unit, uom_id
    )
    select
         p_id , _p_user_id, _p_user_id
        , rs.partner_id, rs.date, rs.partner_code
        , rs.move_id, rs.reference, rs.note
        , p_account_id, rs.account_dest_id
        , rs.credit, rs.debit
        , rs.product_uom_qty, rs.price_unit, rs.uom_id
    from tmp_phat_sinh_trong_ky rs;

    -- kết quả trả về
    return query
    select p_account_id, rs.partner_id
    from tmp_phat_sinh_trong_ky rs;
end
$BODY$;