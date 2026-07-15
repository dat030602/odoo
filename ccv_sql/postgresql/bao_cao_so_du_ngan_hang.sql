/*
    Tính năng: Báo cáo số dư ngân hàng
    Người tạo: Ngochai
    Ngày tạo: 01/06/2024
*/

-- select * from function_bao_cao_so_du_ngan_hang('20220101', '20241212', 'sale', 15)
create or replace function function_bao_cao_so_du_ngan_hang(
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

	-- tính account_account
	drop table if exists tml_account_account;
    create temporary table tml_account_account as
	select DISTINCT aa.id as account_id
	from account_account aa
	where aa.id::text = any(string_to_array(p_account_ids, ','));


	-- tính cuối ky
	drop table if exists tml_bao_cao_so_du_ngan_hang;
    create temporary table tml_bao_cao_so_du_ngan_hang as
	select DISTINCT aml.account_id as account_id
	, (select sum(case
				  when aa3.currency_id is not null and aa3.currency_id != 23 then (aml2.amount_currency) / 2
				  else aml2.debit
				  end
				 ) as debit
	    from account_move_line as aml2
	   	left join account_account aa3 on aml2.account_id = aa3.id
        where aml2.account_id = aa.account_id
        and aml2.date <= p_date_to
        and aml2.parent_state = 'posted'
        ) as debit
    , (select sum(case
				  when aa3.currency_id is not null and aa3.currency_id != 23 then (aml2.amount_currency) / 2
				  else aml2.credit
				  end
				 ) as credit
	    from account_move_line as aml2
	   left join account_account aa3 on aml2.account_id = aa3.id
        where aml2.account_id = aa.account_id
        and aml2.date <= p_date_to
        and aml2.parent_state = 'posted'
        ) as credit
	, aa2.name::json->'vi_VN' #>> '{}' as name_bank
	, aa2.currency_id
	, rpb.acc_number as number_bank
	, rb.name as branch_bank
	from tml_account_account aa
	inner join account_account aa2 on aa2.id = aa.account_id
	left join res_partner_bank rpb on rpb.id = aa2.partner_bank_id
	left join res_bank rb on rb.id = rpb.bank_id
	left join account_move_line aml on aa.account_id = aml.account_id
    where aml.parent_state = 'posted'
		and aml.date <= p_date_to;

	-- Xử lý dữ liệu trên frontend
    delete from alpha_report_line6 where parent_id = p_id;
    insert into alpha_report_line6(
        parent_id, create_uid, write_uid -- bắt buộc
        , account_id
        , end_debit
        , name_bank
		, number_bank
		, branch_bank
    )
    select
         p_id , _p_user_id, _p_user_id
        , rs.account_id
        , case
			when rs.currency_id != 23 then rs.debit + rs.credit
			else rs.debit - rs.credit
		  end
        , rs.name_bank
		, rs.number_bank
		, rs.branch_bank
    from tml_bao_cao_so_du_ngan_hang rs;

    -- kết quả trả về
    return query
    select rs.account_id
    from tml_bao_cao_so_du_ngan_hang rs;
end
$body$;