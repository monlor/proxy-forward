from proxy_manager import ProxyManager
from proxy import Proxy
import sys
import os

if __name__ == '__main__':

    proxy_manager = ProxyManager(
        http_test_url = os.environ.get('HTTP_TEST_URL', 'http://ipinfo.io'),
        https_test_url = os.environ.get('HTTPS_TEST_URL', 'https://ipinfo.io'),
        proxy_list_env = os.environ.get('PROXY_LIST', ''),
        proxy_list_file = os.environ.get('PROXY_LIST_FILE', ''),
        proxy_list_proxy_pool = os.environ.get('PROXY_LIST_PROXY_POOL', ''),
        proxy_mode = os.environ.get('PROXY_MODE', 'default'),
        proxy_change_interval = int(os.environ.get('PROXY_CHANGE_INTERVAL', '0')),
        total_request_threshold = int(os.environ.get('TOTAL_REQUEST_THRESHOLD', '0')),
        proxy_test_interval = int(os.environ.get('PROXY_TEST_INTERVAL', '300'))
    )
    bind_ports_arr = os.environ.get('BIND_PORTS', '8080').split(',')
    bind_ports = [int(port) for port in bind_ports_arr]
    print("启动代理服务...")
    print(f"绑定端口: {bind_ports}")
    proxy = Proxy(proxy_manager, '0.0.0.0', bind_ports)

    try:
        proxy.main_loop()
    except KeyboardInterrupt:
        print("Ctrl C - Stopping server")
        sys.exit(1)
