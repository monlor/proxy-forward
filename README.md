## 介绍

代理转发，将http代理转发到代理池，自动故障转移，随机选择等

## 部署

```
docker run -d --name proxy-forward -p 8080:8080 -e PROXY_LIST=1.1.1.1:80 ghcr.io/monlor/proxy-forward:main
```

## 环境变量

`BIND_PORTS`: 代理转发服务绑定端口，如8080,8081,8082，默认: 8080

`HTTP_TEST_URL`: http测试url，默认: http://ipinfo.io

`HTTPS_TEST_URL`: https测试url，用于测试代理是否支持https，默认: https://ipinfo.io

`PROXY_LIST`: 通过环境变量指定代理，格式: 1.1.1.1:80:http,2.2.2.2:8080:https

`PROXY_LIST_FILE`: 指定csv文件中的代理列表: 1.1.1.1,80,http

`PROXY_LIST_PROXY_POOL`: 指定代理池接口地址，来源项目：[proxy_pool](https://github.com/jhao104/proxy_pool?tab=readme-ov-file)，使用`/all/`接口的地址，如: `http://demo.spiderpy.cn/all/`

`PROXY_MODE`: 代理转发模式，default: 默认，根据条件切换，故障转移；random: 随机，每次请求都切换代理。

`PROXY_CHANGE_INTERVAL`: 根据代理使用时间切换代理，默认空，不开启

`TOTAL_REQUEST_THRESHOLD`: 根据请求数切换代理，默认空，不开启

`PROXY_TEST_INTERVAL`: 代理池故障测试间隔，默认: 300s
