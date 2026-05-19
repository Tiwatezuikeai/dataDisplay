GPU 资源使用看板 使用说明
1. 简介
本看板用于展示 GPU 集群的使用分布与配额消耗情况，基于 FastAPI + ECharts 构建，数据源为 Doris 数据库。

2. 环境要求
Python 3.8+

推荐使用虚拟环境

3. 安装依赖
pip install pymysql pandas "fastapi[standard]"
fastapi[standard] 已包含 uvicorn，无需额外安装。

4. 配置远程数据库连接
编辑项目根目录下的 main.py，修改 DORIS_CONFIG 字典为你实际的环境信息：

doris服务器ip：10.155.2.229:9030

DORIS_CONFIG = {
    "host": "localhost",             # 本地地址（使用远程端口转发获取信息）
    "port": 9030,                    # 端口（通常为 9030）
    "user": "your_user",             # 用户名
    "password": "your_password",     # 密码
    "database": "dw_ailab",          # 数据库名
    "charset": "utf8mb4",
    "connect_timeout": 30,
    "read_timeout": 300,
    "write_timeout": 300,
}
DORIS_CONFIG 中的数据在main.py中有默认值，可自行修改。

远程连接注意事项：
在vscode中使用时，需要配置remote ssh，并配置ssh代理。
连接到对应服务器后，在开启的远程窗口中配置转发端口，端口为"your_doris_host"（doris数据库地址）

如果是本地连接在对应网络中，则将host直接填写为"your_doris_host"（doris数据库地址），不需要配置转发。

5. 启动程序
项目已包含一键启动脚本 start.py，会自动启动后端并打开浏览器：

python start.py
访问地址：http://localhost:8000

若想仅启动后端不打开浏览器，可运行：

uvicorn main:app --host 0.0.0.0 --port 8000
6. 使用看板
选择日期：页面左上角日期选择器，默认当天或最近有数据的日期。

点击“查询”：加载选中日期的 GPU 使用数据和配额数据。

切换集群：从下拉框中选择希望查看的集群，页面图表和明细表格将同步更新。

查看图表：

配额柱状图：展示各资源池的 已消耗 GPU·天、GPU 配额·天 和 算力消耗 GPU·天，柱顶标注配额使用率。

负载饼图：显示当前集群按训练/推理/开发环境等负载类型的使用占比。

展开明细表格：每个图表下方均有“展开明细”按钮，可查看原始数据。

7. 项目文件说明
text
.
├── main.py               # 后端 API（含 Doris 查询、路由）
├── static/
│   └── index.html        # 前端页面（ECharts 图表）
├── start.py              # 一键启动脚本
└── README.md             # 本说明文件
8. 常见问题
柱状图显示错误或空白：检查 Doris 网络连通性，以及配额接口返回数据中是否包含 NaN（已在前端处理，后端也已过滤）。

无法切换集群：确保 api/gpu-usage 和 api/gpu-quota 接口均正常返回数据。

浏览器打开失败：手动访问 http://localhost:8000 即可。