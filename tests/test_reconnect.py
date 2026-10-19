"""Connection lifecycle: no reconnection after unload, one driver, real backoff."""
import asyncio
from unittest.mock import AsyncMock, patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sunology.const import (
    CONF_GATEWAY_HOST, CONF_GATEWAY_PORT, DOMAIN,
    RECONNECT_BACKOFF_BASE, RECONNECT_BACKOFF_MAX,
)


async def _setup(hass):
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_GATEWAY_HOST: "192.168.1.20",
                                                 CONF_GATEWAY_PORT: 20199})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry, entry.runtime_data


async def test_no_reconnection_after_unload(hass):
    connect = AsyncMock()
    with patch("custom_components.sunology.SunologySocket.connect", new=connect):
        entry, ctx = await _setup(hass)
        await asyncio.sleep(0)
        calls_before = connect.await_count

        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()
        # A late disconnection report (receive loop ending) must not reconnect.
        ctx.socket.on_disconnect()
        await asyncio.sleep(0.05)
        await hass.async_block_till_done()

        assert connect.await_count == calls_before
        assert ctx._connect_future is None


async def test_single_connection_driver(hass):
    started = asyncio.Event()
    release = asyncio.Event()

    async def hanging_connect(*args, **kwargs):
        started.set()
        await release.wait()

    with patch("custom_components.sunology.SunologySocket.connect", side_effect=hanging_connect) as connect:
        entry, ctx = await _setup(hass)
        await asyncio.wait_for(started.wait(), 2)
        # The periodic refresh and a stray call both ask while the attempt is pending.
        await ctx.refresh_devices()
        ctx._schedule_connect()
        await asyncio.sleep(0.05)
        assert connect.call_count == 1
        release.set()
        await hass.config_entries.async_unload(entry.entry_id)


async def test_backoff_doubles_and_caps(hass):
    entry, ctx = await _setup(hass)
    delays = []
    for attempt in range(10):
        ctx._connection_atempt = attempt
        delays.append(ctx._reconnect_delay())
    assert delays[:4] == [0, RECONNECT_BACKOFF_BASE, 2 * RECONNECT_BACKOFF_BASE, 4 * RECONNECT_BACKOFF_BASE]
    assert max(delays) == RECONNECT_BACKOFF_MAX
    ctx.on_connect_callback()
    assert ctx._connection_atempt == 0
    await hass.config_entries.async_unload(entry.entry_id)
