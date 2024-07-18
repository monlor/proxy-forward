import os
import threading
import random
import time
import requests
import csv
import concurrent.futures

class ProxyManager:

    def __init__(self, http_test_url='http://ipinfo.io', https_test_url='https://ipinfo.io', proxy_list_env='', proxy_list_file='', proxy_list_proxy_pool='', proxy_mode='default', proxy_change_interval=0, total_request_threshold=0, proxy_test_interval=300):
        # 代理测试URL
        self.http_test_url = http_test_url
        self.https_test_url = https_test_url
        # 代理列表环境变量
        self.proxy_list_env = proxy_list_env
        # 代理列表文件
        self.proxy_list_file = proxy_list_file
        # 代理列表 代理池
        self.proxy_list_proxy_pool = proxy_list_proxy_pool
        # 代理选择模式 random default
        self.proxy_mode = proxy_mode
        # 代理更换间隔
        self.proxy_change_interval = proxy_change_interval
        # 请求计数
        self.total_request_threshold = total_request_threshold
        # 代理测试间隔
        self.proxy_test_interval = proxy_test_interval  
        # init var
        self.available_http_proxies = []
        self.available_https_proxies = []
        self.total_request_count = 0
        self.current_proxies = {}
        self.all_proxies = []
        # init func
        self.load_proxies()
        self.test_proxies_thread()
        

    def load_proxies(self):
        proxy_lists = []

        print("开始加载代理列表...")

        # 从环境变量中加载
        if self.proxy_list_env:
            env_proxies = [tuple(proxy.split(':')) for proxy in self.proxy_list_env.split(',')]
            proxy_lists.extend(env_proxies)
        
        # 从CSV文件中加载
        if self.proxy_list_file:
            with open(self.proxy_list_file, 'r') as file:
                reader = csv.reader(file)
                file_proxies = [tuple(row) for row in reader]
                proxy_lists.extend(file_proxies)
        
        # 通过curl请求获取
        if self.proxy_list_proxy_pool:
            # get请求获取proxy_list_proxy_pool中的内容，是一个数组，取数组中对象中proxy的值
            response = requests.get(self.proxy_list_proxy_pool)
            data = response.json()
            curl_proxies = [tuple(proxy['proxy'].split(':')) for proxy in data]
            proxy_lists.extend(curl_proxies)
        
        # 统一格式化代理列表
        formatted_proxies = []
        for proxy in proxy_lists:
            if len(proxy) == 2:
                formatted_proxies.append((proxy[0], int(proxy[1]), 'http'))
            elif len(proxy) == 3:
                formatted_proxies.append((proxy[0], int(proxy[1]), proxy[2]))

        if not formatted_proxies:
            raise ValueError("代理列表为空")

        print(f"成功加载{len(formatted_proxies)}个代理服务器")
        self.available_http_proxies = formatted_proxies
        self.available_https_proxies = formatted_proxies
        self.all_proxies = formatted_proxies

    def get_random_proxy(self, port, protocol):
        """从列表中随机选择一个代理服务器"""    
        current_key = f'${protocol}-${port}'
        if protocol == 'http':
            self.current_proxies[current_key] = (random.choice(self.available_http_proxies), time.time())
        elif protocol == 'https':
            self.current_proxies[current_key] = (random.choice(self.available_https_proxies), time.time())
        else:
            raise ValueError(f"未知的协议类型: {protocol}")
        return self.current_proxies[current_key][0]

    def get_default_proxy(self, port, protocol):
        if self.total_request_count != 0:
            self.total_request_count += 1
        
        current_key = f'${protocol}-${port}'

        if current_key in self.current_proxies:
            # 根据请求数更换代理
            if self.total_request_threshold != 0 and self.total_request_count >= self.total_request_threshold:
                self.get_random_proxy(port, protocol)
                self.total_request_count = 0
            # 根据时间间隔更换代理
            if self.proxy_change_interval != 0 and time.time() - self.current_proxies[current_key][1] > self.proxy_change_interval:
                self.get_random_proxy(port, protocol)
            # 代理不可用
            if self.current_proxies[current_key][0] not in self.available_http_proxies and self.current_proxies[current_key][0] not in self.available_https_proxies:
                self.get_random_proxy(port, protocol)
        else:
            self.get_random_proxy(port, protocol)
        
        return self.current_proxies[current_key][0]

    def get_proxy(self, port, protocol):
        if not self.available_http_proxies and not self.available_https_proxies:
            raise ValueError("没有可用的代理服务器")
        if self.proxy_mode == 'random':
            return self.get_random_proxy(port, protocol)
        elif self.proxy_mode == 'default':
            return self.get_default_proxy(port, protocol)
        else:
            raise ValueError(f"未知的代理选择模式: {self.proxy_mode}")

    def test_proxy(self, proxy, url):
        host, port, proxy_type = proxy
        try:
            proxies = {'http': f'http://{host}:{port}'}
            response = requests.get(url, proxies=proxies, timeout=10)
            print(f"代理{host}:{port}, {url}, 可用 {response.status_code}")
            return response.status_code == 200
        except Exception as e:
            print(f"代理{host}:{port}, {url}不可用!")
            return False

    def test_proxies(self):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            # 测试http代理
            future_to_proxy_http = {executor.submit(self.test_proxy, proxy, self.http_test_url): proxy for proxy in self.all_proxies}
            new_available_http_proxies = [future_to_proxy_http[future] for future in concurrent.futures.as_completed(future_to_proxy_http) if future.result()]

            if set(self.available_http_proxies) != set(new_available_http_proxies):
                print(f"HTTP代理可用数量: {len(new_available_http_proxies)}")
                self.available_http_proxies = new_available_http_proxies

            # 测试https代理
            future_to_proxy_https = {executor.submit(self.test_proxy, proxy, self.https_test_url): proxy for proxy in self.all_proxies}
            new_available_https_proxies = [future_to_proxy_https[future] for future in concurrent.futures.as_completed(future_to_proxy_https) if future.result()]

            if set(self.available_https_proxies) != set(new_available_https_proxies):
                print(f"HTTPS代理可用数量: {len(new_available_https_proxies)}")
                self.available_https_proxies = new_available_https_proxies

    # def test_proxies(self):
    #     # 分别测试http和https代理
    #     new_available_http_proxies = [proxy for proxy in self.all_proxies if self.test_proxy(proxy, self.http_test_url)]
    #     if set(self.available_http_proxies) != set(new_available_http_proxies):
    #         print(f"HTTP代理可用数量: {len(new_available_http_proxies)}")
    #         self.available_http_proxies = new_available_http_proxies

    #     # 使用多线程测试all_proxies
    #     new_available_https_proxies = [proxy for proxy in self.all_proxies if self.test_proxy(proxy, self.https_test_url)]
    #     if set(self.available_https_proxies) != set(new_available_https_proxies):
    #         print(f"HTTPS代理可用数量: {len(new_available_https_proxies)}")
    #         self.available_https_proxies = new_available_https_proxies

    def test_proxies_thread(self):
        print("启动代理自动测试线程")
        threading.Thread(target=self.periodic_proxy_testing, daemon=True).start()

    def periodic_proxy_testing(self):
        while True:
            self.test_proxies()
            time.sleep(self.proxy_test_interval)
