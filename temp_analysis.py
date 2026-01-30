import pandas as pd

try:
    df = pd.read_csv('data/labels/labels_master.csv', encoding='utf-8-sig')
except:
    df = pd.read_csv('data/labels/labels_master.csv', encoding='cp949')
    
print(f'Total labeled: {len(df)}')
print(f'\nReward distribution:')
print(df['reward'].value_counts().sort_index())
print(f'\nScore_ag vs Reward correlation:')
print(df.groupby('reward')['score_ag'].mean())
print(f'\nCategory distribution:')
print(df['category'].value_counts())
