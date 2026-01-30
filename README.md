# 🏥 ZP Market Monitoring v2 (NLP)

**Last Updated:** 2026-01-30  
AI-powered healthcare news monitoring and analysis system for pharmaceutical business intelligence.

## 🌟 Features

- ✅ **Automated Weekly Crawling**: Collects latest 7 days of pharmaceutical news from Naver
- ✅ **NLP-based Deduplication**: Semantic similarity using Sentence Transformers
- ✅ **Category-Balanced Ranking**: Ensures diverse coverage (Distribution, Client, BD, etc.)
- ✅ **Rule-Based + AI Hybrid**: 70% category scoring + 30% AI prediction
- ✅ **Interactive Dashboard**: Streamlit web interface with real-time filtering
- ✅ **Multi-language Support**: Korean/English translation (Gemini API)
- ✅ **KakaoTalk Summary**: One-click weekly summary generation

## 🎯 System Architecture

### Ranking Algorithm (Current Configuration)

```python
Final Score = 0.7 × Category Score + 0.3 × AI Score

Category Scores:
- Distribution: 6 points
- Client: 5 points
- Zuellig: 5 points
- BD: 4 points
- Others: 3 points

Top 20 Selection:
- Distribution: Top 3 articles
- Client: Top 3 articles
- BD: Top 3 articles
- Zuellig: Top 3 articles
- Other categories: Top 2 each
```

**Why this approach?**
- AI model (AUC ~0.52) has limited predictive power for business-specific relevance
- Rule-based category scoring provides stable, consistent results
- Category balancing prevents single-category dominance

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Naver API credentials (Client ID & Secret)
- Gemini API key (for translation)

### Installation

```bash
pip install -r requirements.txt
```

### Running the Dashboard

```bash
streamlit run dashboard_app.py
```

Or use the batch file (Windows):
```bash
run_dashboard.bat
```

## 📁 Project Structure

```
├── dashboard_app.py              # Main Streamlit dashboard
├── scripts/
│   ├── crawl_naver_news_api.py   # News crawler (7-day lookback)
│   ├── rank_articles.py          # Hybrid ranking engine
│   ├── train_lgbm_model.py       # AI model training (optional)
│   ├── merge_labels.py           # Label management (optional)
│   └── nlp_utils.py              # NLP utilities
├── data/
│   ├── articles_raw/             # Crawled & ranked articles
│   └── labels/                   # Training labels (optional)
├── model/                        # Pre-trained models
│   ├── lgbm_model.txt            # LightGBM model
│   ├── pca.pkl                   # PCA (384→64 dims)
│   └── scaler.pkl                # Feature scaler
└── requirements.txt              # Dependencies
```

## 🔄 Weekly Workflow

### Standard Weekly Update (No Labeling Required)

```bash
# 1. Crawl latest news (past 7 days)
python scripts/crawl_naver_news_api.py

# 2. Rank articles (using existing model)
python scripts/rank_articles.py

# 3. Push to GitHub (auto-deploys to Streamlit Cloud)
git add data/
git commit -m "Weekly update"
git push
```

**Time Required:** ~5 minutes  
**Frequency:** Every Friday morning

## 📊 Performance Metrics

### Current Model Performance (2026-01-30)
- **Test AUC**: 0.52 (near random baseline)
- **Test Accuracy**: 81%
- **Top-5 Reward**: 0.40 (2/5 correct)
- **Training Data**: 542 articles (Nov 2025 - Jan 2026)

### System Value
Despite limited AI performance, the system provides significant value:
- ✅ **10x time savings**: 500+ articles → 20 curated articles
- ✅ **Automated deduplication**: Removes redundant news
- ✅ **Category organization**: Structured by business relevance
- ✅ **Multi-language access**: Instant English translation
- ✅ **Team collaboration**: Shareable dashboard link

**Why low AI performance?**
- News articles require domain knowledge not present in text alone
- Business relevance depends on internal context (competitors, ongoing projects)
- Weekly trend changes make historical patterns less predictive

**Solution:** Rely primarily on rule-based category scoring (70%) with AI as minor adjustment (30%)

## 🎯 Key Technologies

- **NLP**: Sentence Transformers (paraphrase-multilingual-mpnet-base-v2)
- **ML**: LightGBM, PCA (384→64 dims), Scikit-learn
- **Web**: Streamlit
- **Translation**: Gemini 2.0 Flash API, Google Translate (fallback)
- **Crawling**: Naver News Search API

## 🚀 Deployment

### Streamlit Cloud (Recommended)

1. **Push to GitHub** (Private repository)
2. **Connect Streamlit Cloud**: streamlit.io/cloud
3. **Deploy**: Select repository → Auto-deploy
4. **Share link**: Only dashboard visible, code remains private

### Local Deployment

```bash
streamlit run dashboard_app.py
```

Access at: `http://localhost:8501`

## 📝 License

Internal use only - ZP Therapeutics

## � Author

Business Development Team  
ZP Therapeutics Korea
