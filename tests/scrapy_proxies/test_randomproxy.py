from scrapy import Request

from scrapy_proxies import RandomProxy
from tests.conftest import PROXIES


def test_parse_proxies(random_proxy: RandomProxy) -> None:
    assert list(random_proxy.proxies) == PROXIES


def test_process_request(random_proxy: RandomProxy) -> None:
    test_request: Request = Request('http://test_url')

    random_proxy.process_request(test_request, None)

    assert test_request.meta['proxy'] in PROXIES


def test_extracted_from_process_exception(random_proxy: RandomProxy) -> None:
    test_request: Request = Request('http://test_url')
    test_request.meta['proxy'] = PROXIES[-1]

    result = random_proxy._extracted_from_process_exception(test_request)

    assert result == PROXIES[-1]
    assert list(random_proxy.proxies.keys()) == PROXIES[:-1]
