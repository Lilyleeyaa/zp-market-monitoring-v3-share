"""
Merge user feedback from feedback_log.csv into labels_master.csv
Run by GitHub Actions weekly pipeline before model training.
"""
import os
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FEEDBACK_FILE = os.path.join(BASE_DIR, "data", "labels", "feedback_log.csv")
LABELS_FILE = os.path.join(BASE_DIR, "data", "labels", "labels_master.csv")


def merge_feedback():
    """Merge feedback_log.csv into labels_master.csv using URL as key."""
    print("=" * 60)
    print(">>> Merging User Feedback into Training Labels...")
    print("=" * 60)

    # Check if feedback file exists
    if not os.path.exists(FEEDBACK_FILE):
        print("[SKIP] No feedback_log.csv found. Nothing to merge.")
        return

    # Load feedback
    try:
        feedback_df = pd.read_csv(FEEDBACK_FILE, encoding="utf-8")
    except Exception as e:
        print(f"[ERROR] Failed to read feedback_log.csv: {e}")
        return

    if feedback_df.empty or "url" not in feedback_df.columns:
        print("[SKIP] Feedback file is empty or missing 'url' column.")
        return

    print(f"[OK] Loaded {len(feedback_df)} feedback entries")

    # De-duplicate: keep the latest feedback per URL
    feedback_df = feedback_df.sort_values("feedback_date", ascending=False)
    feedback_df = feedback_df.drop_duplicates(subset=["url"], keep="first")
    print(f"[OK] {len(feedback_df)} unique URLs after dedup")

    # Load existing labels
    if not os.path.exists(LABELS_FILE):
        print("[WARN] labels_master.csv not found. Creating from feedback only.")
        # Can't create full labels without raw article data — just log
        print("[INFO] Feedback will be available for next training cycle when raw data exists.")
        return

    try:
        labels_df = pd.read_csv(LABELS_FILE, encoding="utf-8")
    except UnicodeDecodeError:
        labels_df = pd.read_csv(LABELS_FILE, encoding="cp949")

    labels_df["url"] = labels_df["url"].astype(str)
    feedback_df["url"] = feedback_df["url"].astype(str)

    original_count = len(labels_df)

    # Update existing rows: overwrite reward for matching URLs
    matched = labels_df["url"].isin(feedback_df["url"])
    matched_count = matched.sum()

    if matched_count > 0:
        feedback_map = feedback_df.set_index("url")["reward"].to_dict()
        labels_df.loc[matched, "reward"] = labels_df.loc[matched, "url"].map(feedback_map)
        print(f"[OK] Updated reward for {matched_count} existing articles")

    # Add new URLs not in labels_master (these need raw article data to be useful)
    new_urls = feedback_df[~feedback_df["url"].isin(labels_df["url"])]
    if len(new_urls) > 0:
        # Create minimal rows for new feedback entries
        new_rows = []
        for _, fb in new_urls.iterrows():
            new_rows.append({
                "date": fb.get("feedback_date", "")[:10] if pd.notna(fb.get("feedback_date")) else "",
                "category": fb.get("category", ""),
                "published_date": "",
                "site_name": "Naver News",
                "url": fb["url"],
                "title": fb.get("title", ""),
                "summary": "",
                "region": "local",
                "score_ag": fb.get("score_ag", 5),
                "keywords": fb.get("keywords", ""),
                "reward": fb["reward"],
                "rl_score": "",
            })
        new_df = pd.DataFrame(new_rows)
        labels_df = pd.concat([labels_df, new_df], ignore_index=True)
        print(f"[OK] Added {len(new_rows)} new feedback entries")

    # Save updated labels
    labels_df.to_csv(LABELS_FILE, index=False, encoding="utf-8")
    print(f"[OK] labels_master.csv: {original_count} → {len(labels_df)} rows")

    # Archive processed feedback (rename with timestamp)
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    archive_dir = os.path.join(BASE_DIR, "data", "labels", "feedback_archive")
    os.makedirs(archive_dir, exist_ok=True)
    archive_path = os.path.join(archive_dir, f"feedback_{timestamp}.csv")
    os.rename(FEEDBACK_FILE, archive_path)
    print(f"[OK] Archived processed feedback to {archive_path}")

    print("=" * 60)
    print(">>> Feedback Merge Complete!")
    print("=" * 60)


if __name__ == "__main__":
    merge_feedback()
