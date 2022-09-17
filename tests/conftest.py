from typing import Dict

import pytest

from scrapy_proxies.randomproxy import Mode, RandomProxy

PROXIES = [
    'http://proxy1:123123',
    'http://proxy2:123123',
    'http://proxy3:123123',
    'http://proxy4:123123',
]
TEST_FILE_LOCATION = '/tmp/proxies.txt'


@pytest.fixture
def settings(fs) -> Dict:
    fs.create_file(TEST_FILE_LOCATION)
    with open(TEST_FILE_LOCATION, 'w') as fh:
        fh.writelines('\n'.join(PROXIES))
    yield {
        'PROXY_MODE': Mode.RANDOMIZE_PROXY_EVERY_REQUESTS,
        'PROXY_LIST': TEST_FILE_LOCATION,
    }


@pytest.fixture
def random_proxy(settings) -> RandomProxy:
    subject = RandomProxy(settings)
    subject._parse_proxies()
    yield subject
