import difflib
import re
import logging

from odoo import api, models

_logger = logging.getLogger(__name__)

class SmartSearchGenericProvider(models.AbstractModel):
    _name = "smart.search.provider.generic"
    _inherit = "smart.search.provider"
    _description = "Smart Search Generic Provider"
    _smart_search_provider = True

    @api.model
    def search(self, keyword, limit=20):
        configs = self.env["smart.search.config"].search([("active", "=", True)])
        results = []
        for config in configs:
            results.extend(self._search_model(config, keyword, limit))
        return results

    @api.model
    def _search_model(self, config, keyword, limit):
        model = self.env[config.model_name]
        fields = [field.strip() for field in (config.search_field_names or "").split(",") if field.strip()]
        _logger.info("Searching model: %s with fields: %s for keyword: '%s'", config.model_name, fields, keyword)
        if not fields:
            return []
        domain = self._build_domain(fields, keyword)
        _logger.info("Searching model: %s with domain: %s for keyword: '%s'", config.model_name, domain, keyword)
        if not domain:
            return []
        records = model.search(domain, limit=limit)
        if not records:
            return []
        keyword_norm = self._normalize(keyword)
        keyword_boost = self._keyword_boost(config.model_name, keyword_norm)
        results = []
        for record in records:
            display = record.display_name or (record._rec_name and record[record._rec_name]) or str(record.id)
            subtitle = self._get_subtitle(record, config.subtitle_field_name)
            score = self._score_record(record, keyword_norm, fields, display, subtitle, config.model_name)
            score = min(100, score + keyword_boost)
            results.append(
                {
                    "model": config.model_name,
                    "id": record.id,
                    "display": display,
                    "subtitle": subtitle,
                    "icon": config.icon or self.env["ir.model"]._smart_search_default_icon(config.model_name),
                    "score": score,
                }
            )
        return results

    @api.model
    def _build_domain(self, fields, keyword):
        terms = [(field_name, "ilike", keyword) for field_name in fields]
        if not terms:
            return []
        domain = []
        for term in terms[:-1]:
            domain.append("|")
            domain.append(term)
        domain.append(terms[-1])
        return domain

    @api.model
    def _get_subtitle(self, record, field_name):
        if not field_name or field_name not in record._fields:
            return record.display_name
        value = record[field_name]
        if isinstance(value, models.BaseModel):
            return value.display_name
        return value or record.display_name

    @api.model
    def _score_record(self, record, keyword_norm, fields, display, subtitle, model_name):
        candidates = [display, subtitle]
        for field_name in fields:
            if field_name not in record._fields:
                continue
            value = record[field_name]
            if isinstance(value, models.BaseModel):
                candidates.append(value.display_name)
            else:
                candidates.append(value)
        candidates = [self._normalize(value) for value in candidates if value]
        if not candidates:
            return 0
        score = 0
        if model_name == "res.partner" and self._looks_like_contact(keyword_norm):
            score += 10
        if any(candidate == keyword_norm for candidate in candidates):
            score = max(score, 100)
        elif any(candidate.startswith(keyword_norm) for candidate in candidates):
            score = max(score, 90)
        elif any(keyword_norm in candidate for candidate in candidates):
            score = max(score, 70)
        else:
            score = max(score, int(max(difflib.SequenceMatcher(None, keyword_norm, candidate).ratio() for candidate in candidates) * 60))
        return score

    @api.model
    def _keyword_boost(self, model_name, keyword_norm):
        if re.fullmatch(r"[\w.+-]+@[\w.-]+\.[a-z]{2,}", keyword_norm):
            return 30 if model_name == "res.partner" else 0
        if re.fullmatch(r"[0-9+()\s-]{6,}", keyword_norm):
            return 30 if model_name == "res.partner" else 0
        if re.match(r"^SO[0-9]", keyword_norm):
            return 35 if model_name == "sale.order" else 0
        if re.match(r"^PO[0-9]", keyword_norm):
            return 35 if model_name == "purchase.order" else 0
        if re.match(r"^INV[0-9]", keyword_norm):
            return 35 if model_name == "account.move" else 0
        if re.match(r"^(wh/)?(out|in)/", keyword_norm):
            return 35 if model_name == "stock.picking" else 0
        if " " in keyword_norm:
            return 10 if model_name in {"res.partner", "project.task"} else 0
        return 0

    @api.model
    def _normalize(self, value):
        if value is None:
            return ""
        return re.sub(r"\s+", " ", str(value).strip().lower())

    @api.model
    def _looks_like_contact(self, keyword):
        return bool(re.fullmatch(r"[\w.+-]+@[\w.-]+\.[a-z]{2,}", keyword) or re.fullmatch(r"[0-9+()\s-]{6,}", keyword))
