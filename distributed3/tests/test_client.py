from time import sleep

from toolz import merge
from tornado.tcpclient import TCPClient
from tornado import gen
from tornado.ioloop import IOLoop

from distributed import Center, Worker
from distributed.client import (scatter_to_center, scatter_to_workers,
        collect_from_center)
from distributed.core import sync


def test_scatter_delete():
    c = Center('127.0.0.1', 8017)
    a = Worker('127.0.0.1', 8018, c.ip, c.port, ncores=1)
    b = Worker('127.0.0.1', 8019, c.ip, c.port, ncores=1)

    @gen.coroutine
    def f():
        while len(c.ncores) < 2:
            yield asyncio.sleep(0.01, loop=loop)
        data = yield scatter_to_center(c.ip, c.port, [1, 2, 3])

        assert merge(a.data, b.data) == \
                {d.key: i for d, i in zip(data, [1, 2, 3])}

        assert set(c.who_has) == {d.key for d in data}
        assert all(len(v) == 1 for v in c.who_has.values())

        assert [d.get() for d in data] == [1, 2, 3]

        yield data[0]._delete()

        assert merge(a.data, b.data) == \
                {d.key: i for d, i in zip(data[1:], [2, 3])}

        assert data[0].key not in c.who_has

        data = yield scatter_to_workers(c.ip, c.port, [a.address, b.address],
                                        [4, 5, 6])

        m = merge(a.data, b.data)

        for d, v in zip(data, [4, 5, 6]):
            assert m[d.key] == v

        yield a._close()
        yield b._close()
        yield c._close()

    IOLoop.current().run_sync(f)
