import threading
import time
import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


_SMART_SEARCH_CACHE = {}
_SMART_SEARCH_CACHE_LOCK = threading.Lock()
_SMART_SEARCH_CACHE_TTL = 30
_SMART_SEARCH_CACHE_MAX = 256

class SmartSearch(models.AbstractModel):
    _name = "smart.search"
    _description = "Smart Search"

    @api.model
    def search(self, keyword, limit=20):
        keyword = (keyword or "").strip()
        if not keyword:
            return []
        limit = max(1, min(int(limit or 20), 100))
        cache_key = (self.env.uid, self.env.company.id, keyword, limit)
        now = time.monotonic()
        with _SMART_SEARCH_CACHE_LOCK:
            cached = _SMART_SEARCH_CACHE.get(cache_key)
            if cached and cached[0] > now:
                return list(cached[1])

        results = self._search(keyword, limit)

        with _SMART_SEARCH_CACHE_LOCK:
            _SMART_SEARCH_CACHE[cache_key] = (now + _SMART_SEARCH_CACHE_TTL, tuple(results))
            if len(_SMART_SEARCH_CACHE) > _SMART_SEARCH_CACHE_MAX:
                self._prune_cache(now)
        return results

    @api.model
    def _search(self, keyword, limit):
        results = []
        for provider_name in self._get_provider_names():
            provider = self.env.get(provider_name)
            results.extend(provider.search(keyword, limit=limit))
        results = self._deduplicate(results)
        results.sort(key=lambda item: (-item.get("score", 0), item.get("display", ""), item.get("model", "")))
        return results[:limit]

    @api.model
    def _clear_cache(self):
        with _SMART_SEARCH_CACHE_LOCK:
            _SMART_SEARCH_CACHE.clear()

    @api.model
    def _prune_cache(self, now=None):
        now = now or time.monotonic()
        expired_keys = [key for key, (expires_at, _) in _SMART_SEARCH_CACHE.items() if expires_at <= now]
        for key in expired_keys:
            _SMART_SEARCH_CACHE.pop(key, None)
        if len(_SMART_SEARCH_CACHE) > _SMART_SEARCH_CACHE_MAX:
            for key in list(_SMART_SEARCH_CACHE)[: len(_SMART_SEARCH_CACHE) - _SMART_SEARCH_CACHE_MAX]:
                _SMART_SEARCH_CACHE.pop(key, None)

    @api.model
    def _get_provider_names(self):
        provider_names = []
        for model_name, model_class in self.env.registry.models.items():
            if getattr(model_class, "_smart_search_provider", False):
                provider_names.append(model_name)
        return provider_names

    @api.model
    def _deduplicate(self, results):
        unique_results = []
        seen = set()
        for result in results:
            key = (result.get("model"), result.get("id"))
            if key in seen:
                continue
            seen.add(key)
            unique_results.append(result)
        return unique_results

