import os
from dotenv import load_dotenv
import pymysql
import pandas as pd
import math
from fastapi import FastAPI, Query, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# ========== 加载项目目录下的 .env 文件 ==========
load_dotenv()

# ========== 配置（从环境变量读取，避免硬编码）==========
DORIS_CONFIG = {
    "host": os.getenv("DORIS_HOST", "localhost"),
    "port": int(os.getenv("DORIS_PORT", "9030")),
    "user": os.getenv("DORIS_USER", "dw_ailab"),
    "password": os.getenv("DORIS_PASSWORD", ""),
    "database": os.getenv("DORIS_DATABASE", "dw_ailab"),
    "charset": "utf8mb4",
    "connect_timeout": 30,
    "read_timeout": 300,
    "write_timeout": 300,
}

# ========== 原 SQL：GPU 使用分类汇总 ==========
SQL_TEMPLATE = """
SELECT
    cluster,
    team,
    pool_name,
    gpu_model_name,
    load_type,
    COUNT(*) * 60.0 / 86400 AS gpu_days
FROM (
    SELECT
        cluster,
        team,
        pool_name,
        gpu_model_name,
        CASE
          WHEN siflow_type in ('llm-service') then '推理'
          WHEN siflow_type in ('task') THEN '训练'
          WHEN siflow_type in ('general-service', 'deployment') THEN '通用服务'
          WHEN siflow_type in ('vscs', 'jupyter') THEN '开发环境'
          ELSE '其他'
        END AS load_type,
        gpu_util_max,
        gpu_util_avg
    FROM dw_ailab.dws_rm_cluster_team_pool_pod_gpu_gpu_1min_stats_5mini
    WHERE ts_date = %s
      AND pool_name IS NOT NULL
      AND pool_name != ''
) as 1min_stats
GROUP BY cluster, team, pool_name, gpu_model_name, load_type
ORDER BY cluster, team, pool_name, gpu_days DESC
"""

# ========== 新增 SQL：GPU 配额与使用量汇总 ==========
SQL_TEMPLATE_QUOTA = """
    SELECT
        cluster,
        team,
        pool_name,
        ROUND(SUM(used)      * 10.0 / 86400, 4)             AS gpu_days_consumed,
        ROUND(SUM(total)     * 10.0 / 86400, 4)             AS gpu_quota_days,
        ROUND(SUM(gpu_util)  * 10.0 / 100 / 86400, 4)       AS gpu_days_compute,
        CASE
            WHEN SUM(total) > 0 THEN ROUND(SUM(used) / SUM(total) * 100, 2)
            ELSE NULL
        END AS quota_usage_pct
    FROM dw_ailab.dws_rm_cluster_team_pool_gpu_10sec_stats_5mini
    WHERE ts_date = %s
    GROUP BY cluster, team, pool_name
    ORDER BY cluster, team, gpu_days_consumed DESC;
"""

app = FastAPI(title="GPU 使用率看板")
app.mount("/static", StaticFiles(directory="static"), name="static")

# ---------- 工具函数：递归清理 NaN/Inf ----------
def replace_nan_inf(obj):
    """递归遍历对象，将所有 NaN/Inf 替换为 None（JSON null）"""
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    elif isinstance(obj, dict):
        return {k: replace_nan_inf(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [replace_nan_inf(item) for item in obj]
    else:
        return obj

@app.get("/")
async def root():
    return FileResponse("static/index.html")

@app.get("/api/gpu-usage")
async def gpu_usage(date: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$")):
    """根据日期查询 GPU 使用情况（按负载类型分类），返回 JSON"""
    try:
        conn = pymysql.connect(**DORIS_CONFIG)
        df = pd.read_sql(SQL_TEMPLATE, conn, params=[date])
        conn.close()
        data = df.to_dict(orient="records")
        data = replace_nan_inf(data)  # 清理 NaN
        return {"status": "ok", "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"数据库查询失败: {str(e)}")

@app.get("/api/gpu-quota")
async def gpu_quota(date: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$")):
    """根据日期查询 GPU 配额与使用量汇总，返回 JSON"""
    try:
        conn = pymysql.connect(**DORIS_CONFIG)
        df = pd.read_sql(SQL_TEMPLATE_QUOTA, conn, params=[date])
        conn.close()
        data = df.to_dict(orient="records")
        data = replace_nan_inf(data)  # 清理 NaN
        return {"status": "ok", "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"数据库查询失败: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)