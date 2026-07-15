
# TASK: https://erp.icsc.vn/web#id=23733&action=305&model=project.task&view_type=form&cids=1&menu_id=183 



| STT | RULE                                                               | GHI CHÚ           |
| ----| ---------------- --------------------------------------------------| ----------------- |
| 1   | res_partner: portal/public: read access on my commercial partner   | base              |
| 2   | res.partner.rule.private.group                                     | base              |
| 3   | res.partner.rule.use                                               | biz_ccv_account   |
| 4   | res.partner.rule.user.lead                                         | biz_ccv_account   |
| 5   | res.partner.rule.sales.assistant                                   | biz_ccv_account   |
| 6   | Saleadmin                                                          | biz_ccv_account   |

Personal Orders
['&' ,('partner_id','!=',False), ('partner_id.user_id','=',user.id),'|',('user_id','=',user.id),('user_id','=',False)]

sale.order.rule.team.lead


                ['&','&','&',('partner_id', '!=', False),('partner_id.user_id', '!=', False),('partner_id.user_id.team_id', '=',  'team_id.id'),'|','|',('team_id', '=', False),('team_id.user_id', '=', False),('team_id.user_id', '=', user.id)]
            