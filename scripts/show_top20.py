import pandas as pd

df = pd.read_csv('data/articles_raw/articles_ranked_naver_api_20260211.csv', encoding='utf-8')
df_sorted = df.sort_values('final_score', ascending=False)

print('\n=== TOP 20 기사 ===\n')
for idx, (i, row) in enumerate(df_sorted.head(20).iterrows(), 1):
    print(f'{idx}. [{row["category"]}] {row["title"][:60]}')
    print(f'   점수: {row["final_score"]:.3f}\n')
