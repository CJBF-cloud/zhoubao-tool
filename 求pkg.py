import pandas as pd

# 读取 output.xlsx
df = pd.read_excel("output.xlsx")

# 读取 pkg_1.xlsx
pkg_df = pd.read_excel("pkg_1.xlsx")

# 假设 pkg_1.xlsx 里那列列名叫 "pkg"（如果不是就改成实际列名）
pkg_list = pkg_df["pkg"].dropna().unique()

# 过滤，只保留 pkg 在列表中的
filtered_df = df[df["App包名"].isin(pkg_list)]

# 按照 pkg 文件的顺序排序
filtered_df["pkg_sort_order"] = pd.Categorical(
    filtered_df["App包名"], categories=pkg_list, ordered=True
)
filtered_df = filtered_df.sort_values("pkg_sort_order").drop(columns=["pkg_sort_order"])

# 保存结果
filtered_df.to_excel("output_filtered.xlsx", index=False)
print("已生成 output_filtered.xlsx（顺序保持 pkg 文件一致）")