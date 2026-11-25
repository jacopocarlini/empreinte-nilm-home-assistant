"""Vérifie l'export des mesures brutes par jour local."""
import asyncio
import datetime

from ha_stub import TZ, make


async def run():
    co = make()

    async def executor(fn, *args):
        return fn(*args)

    co.hass.async_add_executor_job = executor
    start = datetime.datetime(2026, 4, 2, tzinfo=TZ).timestamp()
    end = start + 86400
    co.store.add_samples([
        (start - 1, 50, 0),
        (start, 100, 10),
        (start + 10, 200, 20),
        (end, 300, 30),
    ])
    co.buffer = [(start + 10, 250, 25), (end, 350, 35)]

    rows = await co.async_export_day("2026-04-02")
    assert rows == [
        [round(start * 1000), 100, 10],
        [round((start + 10) * 1000), 250, 25],
    ], rows

    try:
        await co.async_export_day("not-a-date")
    except ValueError:
        pass
    else:
        raise AssertionError("Invalid dates must be rejected")


asyncio.run(run())
print("OK export brut par jour, buffer, déduplication et date invalide")
