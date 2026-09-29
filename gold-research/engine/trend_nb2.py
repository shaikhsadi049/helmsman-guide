exec(open("blend_warm.py").read().split("for mx in (5, 3):")[0])
full = pd.read_parquet("../trades_v3_reg.parquet"); V = pd.read_parquet("../dt_variants.parquet")[(full.slot != 6).values].reset_index(drop=True)
for c in V.columns:
    DT[:] = np.nan_to_num(V[c].values, nan=0.5)
    for mx in (5, 3): roww(f"{c} max{mx}", mode="tr", mx=mx)
