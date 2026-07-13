import pandas as pd

# 读取原始数据
df = pd.read_excel("output_filtered.xlsx")

# 读取 pkg_1.xlsx，拿到顺序
pkg_df = pd.read_excel("pkg_1.xlsx")
pkg_list = pkg_df["pkg"].dropna().unique()

# 确保时间列是 datetime
df["createdAt"] = pd.to_datetime(df["createdAt"], errors="coerce")
df["updatedAt"] = pd.to_datetime(df["updatedAt"], errors="coerce")

result_rows = []

for pkg, group in df.groupby("App包名"):
    # 找出 updatedAt 最新的那条（排除空值）
    latest_row = group.loc[group["updatedAt"].idxmax()]

    # 插件类型统计
    plugin_counts = group["插件类型"].dropna().value_counts()
    if not plugin_counts.empty:
        top_plugin = plugin_counts.idxmax()
        top_plugin_count = plugin_counts.max()
    else:
        top_plugin = ""
        top_plugin_count = 0

    # 功能分类统计
    func_counts = group["功能分类"].dropna().value_counts()
    if not func_counts.empty:
        top_func = func_counts.idxmax()
        top_func_count = func_counts.max()
    else:
        top_func = ""
        top_func_count = 0

    result_rows.append({
        "recordId": latest_row["recordId"],
        "createdAt": latest_row["createdAt"],
        "updatedAt": latest_row["updatedAt"],
        "App名称": latest_row["App名称"],
        "App包名": pkg,
        "插件类型": top_plugin,
        "功能分类": top_func,
        "插件类型次数": top_plugin_count,
        "功能分类次数": top_func_count
    })

result_df = pd.DataFrame(result_rows)

# ✅ 按 pkg_1.xlsx 的顺序排序
result_df["pkg_sort_order"] = pd.Categorical(
    result_df["App包名"], categories=pkg_list, ordered=True
)
result_df = result_df.sort_values("pkg_sort_order").drop(columns=["pkg_sort_order"])

# 保存结果
result_df.to_excel("注入统计最多出现.xlsx", index=False)
print("已生成 注入统计最多出现.xlsx")