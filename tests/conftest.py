from __future__ import annotations

import asyncio
import importlib.util
import inspect


def pytest_configure(config):
    config.addinivalue_line("markers", "asyncio: run test in an asyncio event loop")


if importlib.util.find_spec("pytest_asyncio") is None:

    def pytest_pyfunc_call(pyfuncitem):
        test_func = pyfuncitem.obj
        if not inspect.iscoroutinefunction(test_func):
            return None

        kwargs = {
            name: pyfuncitem.funcargs[name]
            for name in inspect.signature(test_func).parameters
            if name in pyfuncitem.funcargs
        }
        asyncio.run(test_func(**kwargs))
        return True
