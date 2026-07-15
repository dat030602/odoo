/*
    Tinh nang: Chi tiet cong no phai thu
    Nguoi tao: Ngochai
    Ngay tao: 01/06/2024
*/

-- select * from function_chi_tiet_cong_no_phai_thu('20220101', '20241212', 1, 15, 1)
CREATE OR REPLACE FUNCTION public.function_chi_tiet_cong_no_phai_thu(
    p_date_from timestamp without time zone,
    p_date_to timestamp without time zone,
    p_account_id integer,
    p_partner_id integer,
    p_id integer,
    p_delete boolean DEFAULT true
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
    select tar.create_uid into _p_user_id from alpha_report tar where id = p_id;

    if p_delete then
        delete from alpha_report_line3 where parent_id = p_id;
    end if;

    -- Phat sinh trong ky: lay truc tiep tat ca dong da post tren TK phai thu
    -- cua doi tac, khong phu thuoc move_type hay payment_id.
    drop table if exists tmp_phat_sinh_trong_ky;
    create temporary table tmp_phat_sinh_trong_ky as
    select
        aml.partner_id as partner_id,
        rp.code_contact as partner_code,
        aml.date as date,
        aml.move_id as move_id,
        coalesce(vs.name, am.ref, am.name) as reference,
        aml.quantity as product_uom_qty,
        aml.price_unit as price_unit,
        aml.name as note,
        counterpart.account_dest_id as account_dest_id,
        aml.debit as debit,
        aml.credit as credit,
        aml.product_uom_id as uom_id,
        pp.default_code as default_code,
        pp.id as product_id,
        aml.display_type as display_type,
        am.move_type as move_type,
        aml.id as line_id
    from account_move_line aml
    left join account_move am on am.id = aml.move_id
    left join product_product pp on pp.id = aml.product_id
    left join res_partner rp on rp.id = aml.partner_id
    left join viettel_sinvoice vs on vs.invoice_id = am.id
    left join lateral (
        select aml2.account_id as account_dest_id
        from account_move_line aml2
        where aml2.move_id = aml.move_id
            and aml2.account_id != p_account_id
        order by
            case when aml2.partner_id = p_partner_id then 0 else 1 end,
            aml2.id
        limit 1
    ) counterpart on true
    where aml.account_id = p_account_id
        and aml.partner_id = p_partner_id
        and aml.parent_state = 'posted'
        and aml.date between p_date_from and p_date_to;

    -- So du dau ky tinh tren tat ca phat sinh cua tai khoan cong no.
    drop table if exists tmp_dau_ky;
    create temporary table tmp_dau_ky as
    select
        p_account_id as account_id,
        p_partner_id as partner_id,
        coalesce(sum(aml.debit), 0) as end_debit,
        coalesce(sum(aml.credit), 0) as end_credit
    from account_move_line aml
    where aml.account_id = p_account_id
        and aml.partner_id = p_partner_id
        and aml.parent_state = 'posted'
        and aml.date < p_date_from;

    insert into alpha_report_line3(
        parent_id, create_uid, write_uid,
        note, partner_id, account_id,
        end_debit, end_credit
    )
    select
        p_id, _p_user_id, _p_user_id,
        'Số dư đầu kỳ', rs.partner_id, p_account_id,
        case
            when rs.end_debit - rs.end_credit > 0 then rs.end_debit - rs.end_credit
            else 0
        end as end_debit,
        case
            when rs.end_credit - rs.end_debit > 0 then rs.end_credit - rs.end_debit
            else 0
        end as end_credit
    from tmp_dau_ky rs
    where rs.end_debit - rs.end_credit <> 0
        or exists (select 1 from tmp_phat_sinh_trong_ky);

    insert into alpha_report_line3(
        parent_id, create_uid, write_uid,
        partner_id, date, partner_code,
        move_id, reference, note,
        account_id, account_dest_id,
        debit, credit,
        product_uom_qty, price_unit, uom_id,
        default_code, product_id,
        display_type, move_type
    )
    select
        p_id, _p_user_id, _p_user_id,
        rs.partner_id, rs.date, rs.partner_code,
        rs.move_id, rs.reference, rs.note,
        p_account_id, rs.account_dest_id,
        rs.debit, rs.credit,
        rs.product_uom_qty, rs.price_unit, rs.uom_id,
        rs.default_code, rs.product_id,
        rs.display_type, rs.move_type
    from tmp_phat_sinh_trong_ky rs
    order by rs.date, rs.move_id, rs.line_id;

    return query
    select distinct p_account_id, rs.partner_id
    from tmp_phat_sinh_trong_ky rs;
end
$BODY$;
