#免费代理IP池
高频抓取某个网站的数据，很有可能就被网站管理员封掉IP，导致抓取数据失败，解决这个问题最直接，简单的方法就是使用代理IP。目前网上有不少提供付费代理IP的平台，但是如需长期使用，该方案是笔不少的开销。本项目通过抓取IP代理网站提供免费代理IP，并不间断的验证IP的有效性，根据代理IP验证的历史记录对IP进行评估，输出高质量代理IP。
**源码：**https://github.com/clelandgt/ip_proxy

##功能
- 100+ 支持https, 匿名或高匿名的免费代理IP;
- 外部提供API调用。

##原理
第一步：爬取多个免费IP代理网站获得代理IP;
第二步：访问https://www.baidu.com/验证代理IP的有效性和响应时间，由于每次都能爬取10000+个代理，需要使用并发(多进程+协程)方式快速完成验证;
第三步：将验证通过的代理IP存入mongodb中；
第四步：睡眠一定时间；
第五步：开始验证数据库中的IP，根据每个IP的历史失败数和失败率淘汰掉一些低质量或失效的代理IP;
第六步：验证完数据库中的IP，如果数据库中的IP小于一个预设值(比如100)，执行第一步，否则执行第四步。
![这里写图片描述](http://img.blog.csdn.net/20170222220015846?watermark/2/text/aHR0cDovL2Jsb2cuY3Nkbi5uZXQvZ2FuemhleXU=/font/5a6L5L2T/fontsize/400/fill/I0JBQkFCMA==/dissolve/70/gravity/SouthEast)

##部署
- os：Centos7
- redis 2.8.19
- mongodb 3.4.1
- nginx 1.10.2

完成以上系统和软件的安装，其中操作系统可以选择其他linux版本，软件版本没有特殊要求。

###克隆代码到本地
	$ git clone https://github.com/clelandgt/ip_proxy

### 创建虚拟环境
	$ mkvirtualenv proxy_env #创建名为proxy_env的虚拟环境
	$ workon proxy_env #加载proxy_env虚拟环境
	$ pip install -r requirements.txt #导入并安装需要安装的第三方库
关于虚拟环境的详细介绍和使用详见：http://blog.csdn.net/ganzheyu/article/details/53014726

### supervisord
使用supervisord进行进程管理，当进程出现异常退出时，supervisord会重新启动该进程。

	$ pip install supervisor #安装supervisord
	$ mv supervisord.conf /etc/supervisord.conf #默认配置文件在/etc下，所以将项目配置好的deploy目录下的supervisord.conf拷贝到/etc下。

本项目需要监控的进程主要有两个，一个是IP代理核心流程"python ip_proxy.py"，另一个是提供外部API访问的"uwsgi uwsgi.ini"

	[program:proxy_crawler]
	command=python ip_proxy.py
	directory=/root/webapp/ip_proxy/src/ip_proxy
	autostart=true
	autorestart=true
	stdout_logfile=/tmp/proxy_crawler.log

	[program:uwsgi]
	command=uwsgi uwsgi.ini
	directory=/root/webapp/ip_proxy/src
	autostart=true
	autorestart=true

### nginx + uwsgi 配置后台服务
	...

### 设置开机自启
	$ systemctl enabled supervisord.service #设置supervisord开机自启
	$ systemctl enabled redis.service #设置redis开机自启
	$ systemctl enabled mongod.service #设置mongodb开机自启
	$ systemctl enabled nginx.service #设置nginx开机自启

关于systemctl详细使用见：http://blog.csdn.net/ganzheyu/article/details/56335419
