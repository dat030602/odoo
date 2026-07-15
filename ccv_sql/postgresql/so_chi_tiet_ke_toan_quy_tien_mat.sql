/*
    Tính năng: Sổ kế toán chi tiết quỹ tiền mặt
    Người tạo: Ngochai
    Ngày tạo: 01/06/2024
*/

-- select * from function_so_chi_tiet_ke_toan_quy_tien_mat('20220101', '20241212', 'sale', 15)
CREATE OR REPLACE FUNCTION public.function_so_chi_tiet_ke_toan_quy_tien_mat(
	p_date_from timestamp without time zone,
	p_date_to timestamp without time zone,
	p_account_id integer,
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
    from account_move_line aml
	left join account_move am on am.id = aml.move_id
    where aml.parent_state = 'posted'
		and p_account_id = aml.account_id
		and(p_date_from <= aml.date and aml.date <= p_date_to);

	-- tính nợ có đầu kỳ
    drop table if exists tmp_dau_ky;
    create temporary table tmp_dau_ky as
    select tcc.account_id as account_id
		, (select sum(aml.debit) as start_debit from account_move_line as aml
			where aml.account_id = tcc.account_id
			and aml.date < p_date_from
			and aml.parent_state = 'posted'
		  	) as end_debit
		, (select sum(aml.credit) as start_credit from account_move_line as aml
			where aml.account_id = tcc.account_id
			and aml.date < p_date_from
			and aml.parent_state = 'posted'
		  	) as end_credit
    from tmp_account_account tcc;

	-- Insert dau ky truoc
    delete from alpha_report_line4 where parent_id = p_id;
    insert into alpha_report_line4(
        parent_id, create_uid, write_uid -- bắt buộc
        , note, account_id
		, end_debit, end_credit
    )
    select
         p_id , _p_user_id, _p_user_id
        , 'Số dư đầu kỳ', p_account_id
        , CASE
		  WHEN rs.end_debit - rs.end_credit > 0 THEN rs.end_debit - rs.end_credit
		  ELSE 0
          END AS end_debit
        , CASE
              WHEN rs.end_credit - rs.end_debit > 0 THEN rs.end_credit - rs.end_debit
              ELSE 0
          END AS end_credit
    from tmp_dau_ky rs;

	-- Tính phát sinh trong ky
    drop table if exists tmp_phat_sinh_trong_ky;
    create temporary table tmp_phat_sinh_trong_ky as
    select
		aml.partner_id as partner_id
        , aml.date as date_confirm
		, aml.date as date
		, aml.move_id as move_id
		, am.ref as reference
		, aml.name as note
		, aml.account_id as account_id
		, (SELECT (string_to_array(array_to_string(array(
			select aml2.account_id
			from account_move_line aml2
			where aml2.move_id = aml.move_id
			and CASE
				  WHEN aml.debit > 0 THEN aml2.credit > 0
				  ELSE aml2.debit > 0
			  END
		  	), ',', '0'), ',')::INT[])[1]) as account_dest_id
		, aml.debit as debit
		, aml.credit as credit
    from account_move_line aml
	left join account_move am on am.id = aml.move_id

    where (p_date_from <= aml.date and aml.date <= p_date_to)
		and aml.parent_state = 'posted'
		and p_account_id = aml.account_id
	ORDER BY aml.date;

	-- insert dữ liệu phát sinh trong ky
    insert into alpha_report_line4(
        parent_id, create_uid, write_uid -- bắt buộc
        , partner_id, date
		, move_id
		, move2_id
		, reference, note
		, account_id, account_dest_id
		, debit, credit
    )
    select
         p_id , _p_user_id, _p_user_id
        , rs.partner_id, rs.date
		, case
		  when rs.debit > 0 then rs.move_id
		  else Null
		  end
	  	, case
		  when rs.credit > 0 then rs.move_id
		  else Null
		  end
		, rs.reference, rs.note
		, p_account_id, rs.account_dest_id
        , rs.debit, rs.credit
    from tmp_phat_sinh_trong_ky rs;

    -- kết quả trả về
    return query
    select p_account_id, rs.partner_id
    from tmp_phat_sinh_trong_ky rs;
end
$BODY$;