import httpx
import pytest
import respx

from app.market.massive import MassiveMarketDataSource

SNAPSHOT_URL_REGEX = r".*/v2/snapshot/.*"


@pytest.mark.asyncio
@respx.mock
async def test_get_prices_parses_snapshot():
    respx.get(url__regex=SNAPSHOT_URL_REGEX).mock(
        return_value=httpx.Response(
            200,
            json={"tickers": [{"ticker": "AAPL", "lastTrade": {"p": 190.42}}]},
        )
    )
    source = MassiveMarketDataSource(api_key="test-key")
    await source.start()
    prices = await source.get_prices(["AAPL"])
    assert prices == {"AAPL": 190.42}
    await source.stop()


@pytest.mark.asyncio
@respx.mock
async def test_get_prices_parses_multiple_tickers():
    respx.get(url__regex=SNAPSHOT_URL_REGEX).mock(
        return_value=httpx.Response(
            200,
            json={
                "tickers": [
                    {"ticker": "AAPL", "lastTrade": {"p": 190.42}},
                    {"ticker": "GOOGL", "lastTrade": {"p": 175.10}},
                ]
            },
        )
    )
    source = MassiveMarketDataSource(api_key="test-key")
    await source.start()
    prices = await source.get_prices(["AAPL", "GOOGL"])
    assert prices == {"AAPL": 190.42, "GOOGL": 175.10}
    await source.stop()


@pytest.mark.asyncio
async def test_get_prices_empty_ticker_list_returns_empty_without_request():
    source = MassiveMarketDataSource(api_key="test-key")
    await source.start()
    with respx.mock:
        # No route registered: any actual HTTP call would raise.
        prices = await source.get_prices([])
    assert prices == {}
    await source.stop()


@pytest.mark.asyncio
@respx.mock
async def test_rate_limit_returns_empty_dict_not_raise():
    respx.get(url__regex=SNAPSHOT_URL_REGEX).mock(return_value=httpx.Response(429))
    source = MassiveMarketDataSource(api_key="test-key")
    await source.start()
    prices = await source.get_prices(["AAPL"])
    assert prices == {}
    await source.stop()


@pytest.mark.asyncio
@respx.mock
async def test_not_authorized_returns_empty_dict_not_raise():
    respx.get(url__regex=SNAPSHOT_URL_REGEX).mock(
        return_value=httpx.Response(403, json={"status": "NOT_AUTHORIZED"})
    )
    source = MassiveMarketDataSource(api_key="test-key")
    await source.start()
    prices = await source.get_prices(["AAPL"])
    assert prices == {}
    await source.stop()


@pytest.mark.asyncio
@respx.mock
async def test_server_error_returns_empty_dict_not_raise():
    respx.get(url__regex=SNAPSHOT_URL_REGEX).mock(return_value=httpx.Response(500))
    source = MassiveMarketDataSource(api_key="test-key")
    await source.start()
    prices = await source.get_prices(["AAPL"])
    assert prices == {}
    await source.stop()


@pytest.mark.asyncio
@respx.mock
async def test_malformed_json_returns_empty_dict_not_raise():
    respx.get(url__regex=SNAPSHOT_URL_REGEX).mock(
        return_value=httpx.Response(200, content=b"not json")
    )
    source = MassiveMarketDataSource(api_key="test-key")
    await source.start()
    prices = await source.get_prices(["AAPL"])
    assert prices == {}
    await source.stop()


@pytest.mark.asyncio
@respx.mock
async def test_missing_ticker_in_response_is_simply_omitted():
    respx.get(url__regex=SNAPSHOT_URL_REGEX).mock(
        return_value=httpx.Response(200, json={"tickers": []})
    )
    source = MassiveMarketDataSource(api_key="test-key")
    await source.start()
    prices = await source.get_prices(["ZZZZ_UNKNOWN"])
    assert prices == {}
    await source.stop()


@pytest.mark.asyncio
@respx.mock
async def test_ticker_without_last_trade_is_omitted():
    respx.get(url__regex=SNAPSHOT_URL_REGEX).mock(
        return_value=httpx.Response(
            200,
            json={"tickers": [{"ticker": "AAPL", "prevDay": {"c": 189.80}}]},
        )
    )
    source = MassiveMarketDataSource(api_key="test-key")
    await source.start()
    prices = await source.get_prices(["AAPL"])
    assert prices == {}
    await source.stop()


@pytest.mark.asyncio
@respx.mock
async def test_transient_network_error_retries_then_succeeds():
    route = respx.get(url__regex=SNAPSHOT_URL_REGEX)
    route.side_effect = [
        httpx.TimeoutException("timed out"),
        httpx.Response(200, json={"tickers": [{"ticker": "AAPL", "lastTrade": {"p": 190.42}}]}),
    ]
    source = MassiveMarketDataSource(api_key="test-key")
    source.RETRY_BACKOFF_SECONDS = 0.0  # keep the test fast
    await source.start()
    prices = await source.get_prices(["AAPL"])
    assert prices == {"AAPL": 190.42}
    assert route.call_count == 2
    await source.stop()


@pytest.mark.asyncio
@respx.mock
async def test_transient_network_error_gives_up_after_max_retries():
    route = respx.get(url__regex=SNAPSHOT_URL_REGEX)
    route.side_effect = httpx.TimeoutException("timed out")
    source = MassiveMarketDataSource(api_key="test-key")
    source.RETRY_BACKOFF_SECONDS = 0.0
    await source.start()
    prices = await source.get_prices(["AAPL"])
    assert prices == {}
    assert route.call_count == source.MAX_TRANSIENT_RETRIES + 1
    await source.stop()


@pytest.mark.asyncio
@respx.mock
async def test_is_valid_ticker_true_when_snapshot_returns_ticker():
    respx.get(url__regex=SNAPSHOT_URL_REGEX).mock(
        return_value=httpx.Response(
            200, json={"tickers": [{"ticker": "AAPL", "lastTrade": {"p": 190.42}}]}
        )
    )
    source = MassiveMarketDataSource(api_key="test-key")
    await source.start()
    assert await source.is_valid_ticker("AAPL") is True
    await source.stop()


@pytest.mark.asyncio
@respx.mock
async def test_is_valid_ticker_false_when_snapshot_empty():
    respx.get(url__regex=SNAPSHOT_URL_REGEX).mock(
        return_value=httpx.Response(200, json={"tickers": []})
    )
    source = MassiveMarketDataSource(api_key="test-key")
    await source.start()
    assert await source.is_valid_ticker("ZZZZ_NOT_REAL") is False
    await source.stop()


@pytest.mark.asyncio
@respx.mock
async def test_is_valid_ticker_false_on_error_status():
    respx.get(url__regex=SNAPSHOT_URL_REGEX).mock(return_value=httpx.Response(500))
    source = MassiveMarketDataSource(api_key="test-key")
    await source.start()
    assert await source.is_valid_ticker("AAPL") is False
    await source.stop()


@pytest.mark.asyncio
@respx.mock
async def test_is_valid_ticker_false_on_network_error():
    respx.get(url__regex=SNAPSHOT_URL_REGEX).mock(side_effect=httpx.ConnectError("boom"))
    source = MassiveMarketDataSource(api_key="test-key")
    await source.start()
    assert await source.is_valid_ticker("AAPL") is False
    await source.stop()


@pytest.mark.asyncio
async def test_auth_header_uses_bearer_token_not_query_param():
    source = MassiveMarketDataSource(api_key="secret-key-123")
    await source.start()
    assert source._client.headers["Authorization"] == "Bearer secret-key-123"
    await source.stop()


@pytest.mark.asyncio
async def test_get_prices_raises_if_called_before_start():
    source = MassiveMarketDataSource(api_key="test-key")
    with pytest.raises(AssertionError):
        await source.get_prices(["AAPL"])


@pytest.mark.asyncio
async def test_stop_is_safe_to_call_without_start():
    source = MassiveMarketDataSource(api_key="test-key")
    await source.stop()  # must not raise
