"""
Kesari AI — Real-Time Data Tool
Fetches live weather, crypto prices, and stock data from free public APIs.
No API keys required for any of these sources.
"""
import asyncio
import logging
import json
from kesari.tools.base_tool import BaseTool
from kesari.tools.knowledge_cache_tool import get_cache, TTL_SHORT, TTL_MEDIUM

logger = logging.getLogger(__name__)


async def _http_get(url: str, headers: dict = None) -> dict | list | None:
    """Async HTTP GET returning parsed JSON."""
    import urllib.request
    import urllib.error
    loop = asyncio.get_event_loop()
    def _fetch():
        req = urllib.request.Request(url, headers=headers or {
            "User-Agent": "KesariAI/1.0",
            "Accept": "application/json",
        })
        with urllib.request.urlopen(req, timeout=8) as resp:
            return json.loads(resp.read())
    try:
        return await loop.run_in_executor(None, _fetch)
    except Exception as e:
        logger.debug(f"HTTP GET failed {url}: {e}")
        return None


# ── Weather ───────────────────────────────────────────────

CITY_COORDS = {
    "mumbai": (19.0760, 72.8777),
    "delhi": (28.7041, 77.1025),
    "bangalore": (12.9716, 77.5946),
    "bengaluru": (12.9716, 77.5946),
    "hyderabad": (17.3850, 78.4867),
    "chennai": (13.0827, 80.2707),
    "kolkata": (22.5726, 88.3639),
    "pune": (18.5204, 73.8567),
    "ahmedabad": (23.0225, 72.5714),
    "jaipur": (26.9124, 75.7873),
    "london": (51.5074, -0.1278),
    "new york": (40.7128, -74.0060),
    "tokyo": (35.6762, 139.6503),
    "paris": (48.8566, 2.3522),
    "sydney": (-33.8688, 151.2093),
    "dubai": (25.2048, 55.2708),
    "singapore": (1.3521, 103.8198),
}

WMO_CODES = {
    0: "☀️ Clear sky", 1: "🌤️ Mainly clear", 2: "⛅ Partly cloudy", 3: "☁️ Overcast",
    45: "🌫️ Fog", 48: "🌫️ Icy fog",
    51: "🌦️ Light drizzle", 53: "🌦️ Moderate drizzle", 55: "🌧️ Dense drizzle",
    61: "🌧️ Slight rain", 63: "🌧️ Moderate rain", 65: "🌧️ Heavy rain",
    71: "🌨️ Slight snow", 73: "🌨️ Moderate snow", 75: "❄️ Heavy snow",
    80: "🌦️ Rain showers", 81: "🌧️ Moderate showers", 82: "⛈️ Violent showers",
    95: "⛈️ Thunderstorm", 96: "⛈️ Thunderstorm w/ hail", 99: "⛈️ Heavy thunderstorm",
}


async def get_weather(city: str) -> dict:
    city_lower = city.lower().strip()
    coords = CITY_COORDS.get(city_lower)
    if not coords:
        # Try geocoding via Open-Meteo's geocoding
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&format=json"
        geo_data = await _http_get(geo_url)
        if geo_data and geo_data.get("results"):
            r = geo_data["results"][0]
            coords = (r["latitude"], r["longitude"])
            city = r.get("name", city)
        else:
            return {"error": f"Could not find city: {city}"}

    lat, lon = coords
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&current=temperature_2m,relative_humidity_2m,wind_speed_10m,weathercode"
        f"&temperature_unit=celsius&wind_speed_unit=kmh&timezone=auto"
    )
    data = await _http_get(url)
    if not data:
        return {"error": "Could not fetch weather data"}

    current = data.get("current", {})
    code = current.get("weathercode", 0)
    return {
        "city": city,
        "temperature": f"{current.get('temperature_2m', 'N/A')}°C",
        "condition": WMO_CODES.get(code, "Unknown"),
        "humidity": f"{current.get('relative_humidity_2m', 'N/A')}%",
        "wind_speed": f"{current.get('wind_speed_10m', 'N/A')} km/h",
        "type": "weather",
    }


# ── Crypto ────────────────────────────────────────────────

CRYPTO_IDS = {
    "bitcoin": "bitcoin", "btc": "bitcoin",
    "ethereum": "ethereum", "eth": "ethereum",
    "bnb": "binancecoin",
    "xrp": "ripple", "ripple": "ripple",
    "solana": "solana", "sol": "solana",
    "cardano": "cardano", "ada": "cardano",
    "dogecoin": "dogecoin", "doge": "dogecoin",
    "usdt": "tether", "tether": "tether",
    "polkadot": "polkadot", "dot": "polkadot",
}


async def get_crypto(symbol: str) -> dict:
    symbol_lower = symbol.lower().strip()
    coin_id = CRYPTO_IDS.get(symbol_lower, symbol_lower)
    url = (
        f"https://api.coingecko.com/api/v3/simple/price"
        f"?ids={coin_id}&vs_currencies=usd,inr"
        f"&include_24hr_change=true&include_market_cap=true"
    )
    data = await _http_get(url)
    if not data or coin_id not in data:
        return {"error": f"Could not fetch data for: {symbol}"}

    info = data[coin_id]
    change_24h = info.get("usd_24h_change", 0)
    trend = "📈" if change_24h >= 0 else "📉"
    return {
        "symbol": symbol.upper(),
        "coin_id": coin_id,
        "price_usd": f"${info.get('usd', 0):,.2f}",
        "price_inr": f"₹{info.get('inr', 0):,.0f}",
        "change_24h": f"{change_24h:+.2f}%",
        "trend": trend,
        "market_cap_usd": f"${info.get('usd_market_cap', 0):,.0f}",
        "type": "crypto",
    }


# ── Stocks ────────────────────────────────────────────────

async def get_stock(symbol: str) -> dict:
    """Fetch stock data via Yahoo Finance public JSON API."""
    symbol_upper = symbol.upper().strip()
    # Add .NS for NSE Indian stocks if no exchange suffix
    if "." not in symbol_upper and len(symbol_upper) <= 8:
        nse_symbol = symbol_upper + ".NS"
    else:
        nse_symbol = symbol_upper

    async def _try_symbol(sym: str) -> dict | None:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range=1d"
        data = await _http_get(url, headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
        })
        if not data:
            return None
        try:
            result = data["chart"]["result"][0]
            meta = result["meta"]
            price = meta.get("regularMarketPrice", 0)
            prev_close = meta.get("chartPreviousClose", meta.get("previousClose", price))
            change = price - prev_close
            change_pct = (change / prev_close * 100) if prev_close else 0
            currency = meta.get("currency", "USD")
            trend = "📈" if change >= 0 else "📉"
            return {
                "symbol": sym,
                "name": meta.get("shortName", sym),
                "price": f"{price:.2f} {currency}",
                "change": f"{change:+.2f}",
                "change_pct": f"{change_pct:+.2f}%",
                "trend": trend,
                "exchange": meta.get("exchangeName", ""),
                "type": "stock",
            }
        except (KeyError, IndexError, TypeError):
            return None

    result = await _try_symbol(nse_symbol) or await _try_symbol(symbol_upper)
    return result or {"error": f"Could not fetch stock data for: {symbol}"}


# ── Unified Tool ──────────────────────────────────────────

async def get_realtime_data(data_type: str, query: str) -> dict:
    cache = get_cache()
    cache_key = f"realtime:{data_type}:{query.lower()}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    if data_type == "weather":
        result = await get_weather(query)
        ttl = TTL_MEDIUM
    elif data_type == "crypto":
        result = await get_crypto(query)
        ttl = TTL_SHORT
    elif data_type == "stock":
        result = await get_stock(query)
        ttl = TTL_SHORT
    else:
        result = {"error": f"Unknown data type: {data_type}"}
        ttl = TTL_SHORT

    if "error" not in result:
        cache.set(cache_key, result, ttl=ttl, intent="realtime", source=data_type)
    return result


class RealtimeDataTool(BaseTool):
    name = "realtime_data"
    description = (
        "Fetch live real-time data: weather, cryptocurrency prices, or stock prices. "
        "Use this when user asks about weather, temperature, crypto/bitcoin/eth price, "
        "stock price, or any live financial/environmental data."
    )
    parameters = {
        "data_type": {
            "type": "string",
            "description": "Type of data: 'weather', 'crypto', or 'stock'",
        },
        "query": {
            "type": "string",
            "description": "City name for weather, coin name for crypto (bitcoin/eth), or stock ticker",
        },
    }

    async def execute(self, **kwargs) -> str:
        data_type = kwargs.get("data_type", "").lower()
        query = kwargs.get("query", "")
        if not data_type or not query:
            return "Error: data_type and query are required."
        result = await get_realtime_data(data_type, query)
        return json.dumps(result, ensure_ascii=False)
