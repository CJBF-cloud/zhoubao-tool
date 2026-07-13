import pandas as pd

# 读取文件
df = pd.read_excel("output.xlsx")
pkg_df = pd.read_excel("pkg_2.xlsx")

# 定义注入脚本类型的优先级
priority = {"针对百度系App": 1, "针对通用App": 2, "针对特定App": 3}

def choose_top(group):
    result = {}
    # App包名
    result["App包名"] = group["App包名"].iloc[0]
    # App名称：取 updatedAt 最新的一条
    latest_row = group.sort_values("updatedAt", ascending=False).iloc[0]
    result["App名称"] = latest_row["App名称"]

    # 插件类型：根据优先级选
    group["优先级"] = group["插件类型"].map(priority)
    best_type = group.sort_values("优先级").iloc[0]["插件类型"]
    result["插件类型"] = best_type
    result["注入脚本类型命中次数"] = (group["插件类型"] == best_type).sum()

    # 功能分类：按次数选
    func_counts = group["功能分类"].value_counts()
    if not func_counts.empty:
        best_func = func_counts.idxmax()
        result["功能分类"] = best_func
        result["功能分类命中次数"] = func_counts.max()
    else:
        result["功能分类"] = "无"
        result["功能分类命中次数"] = 0

    return pd.Series(result)

# 分组处理已有数据
grouped = df.groupby("App包名").apply(choose_top).reset_index(drop=True)

# 构造完整结果，严格按照 pkg 文件顺序
final_rows = []
for pkg in pkg_df["pkg"]:
    if pkg in grouped["App包名"].values:
        row = grouped[grouped["App包名"] == pkg].iloc[0].to_dict()
    else:
        row = {
            "App包名": pkg,
            "App名称": "无",
            "插件类型": "无",
            "注入脚本类型命中次数": 0,
            "功能分类": "无",
            "功能分类命中次数": 0
        }
    final_rows.append(row)

final_df = pd.DataFrame(final_rows)

# 保存结果
final_df.to_excel("注入次数优先级选择最终2合并.xlsx", index=False)
print("处理完成，结果已保存到 注入次数优先级选择最终2合并.xlsx")