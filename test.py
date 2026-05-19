"""
GPU 使用看板 - 本地测试脚本
用法：python test.py <日期>  [可选参数]
示例：python test.py 2026-04-23
      python test.py 2026-04-23 --usage-only   # 只查使用明细
      python test.py 2026-04-23 --quota-only   # 只查配额汇总
"""
import pymysql
import pandas as pd
import sys
import argparse
from tabulate import tabulate  # 可选，让表格更好看；若无此库自动降级

# ========== 数据库配置（与 main.py 相同）==========
DORIS_CONFIG = {
    "host": "localhost",
    "port": 9030,
    "user": "dw_ailab",
    "password": "A*gG8i4Pk2D^gHz7",
    "database": "dw_ailab",
    "charset": "utf8mb4",
    "connect_timeout": 30,
    "read_timeout": 300,
    "write_timeout": 300,
}

# ========== SQL 模板（与 main.py 完全一致）==========
SQL_USAGE = """
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

SQL_QUOTA = """
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

def query_to_df(sql, params, description):
    """执行查询并返回 DataFrame"""
    print(f"\n{'='*60}")
    print(f"  查询: {description}")
    print(f"  参数: {params}")
    print(f"{'='*60}")
    try:
        conn = pymysql.connect(**DORIS_CONFIG)
        df = pd.read_sql(sql, conn, params=params)
        conn.close()
        return df
    except Exception as e:
        print(f"❌ 查询失败: {e}")
        return pd.DataFrame()

def pretty_print(df, title):
    """美化打印 DataFrame"""
    if df.empty:
        print(f"⚠️  {title} 无数据")
        return
    print(f"\n📋 {title} (共 {len(df)} 条)")
    try:
        # 尝试使用 tabulate 获得更好效果
        from tabulate import tabulate
        print(tabulate(df, headers='keys', tablefmt='psql', showindex=False, floatfmt=".4f"))
    except ImportError:
        # 降级为 pandas 默认显示
        with pd.option_context('display.max_rows', None, 'display.max_columns', None,
                               'display.width', 200, 'display.float_format', '{:.4f}'.format):
            print(df.to_string(index=False))

def main():
    parser = argparse.ArgumentParser(description="GPU 看板数据本地测试")
    parser.add_argument("date", help="查询日期，格式 YYYY-MM-DD")
    parser.add_argument("--usage-only", action="store_true", help="仅查询 GPU 使用明细")
    parser.add_argument("--quota-only", action="store_true", help="仅查询配额汇总")
    args = parser.parse_args()

    date = args.date
    # 简单校验日期格式
    if len(date) != 10 or date[4] != '-' or date[7] != '-':
        print("❌ 日期格式错误，请使用 YYYY-MM-DD")
        sys.exit(1)

    run_usage = not args.quota_only
    run_quota = not args.usage_only

    if run_usage:
        df_usage = query_to_df(SQL_USAGE, [date], "GPU 使用明细（按负载类型分）")
        pretty_print(df_usage, "GPU 使用明细")

    if run_quota:
        df_quota = query_to_df(SQL_QUOTA, [date], "GPU 配额与使用汇总")
        pretty_print(df_quota, "GPU 配额汇总")

if __name__ == "__main__":
    # 可选安装 tabulate 让输出更整齐: pip install tabulate
    main()