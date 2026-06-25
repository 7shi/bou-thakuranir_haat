# 日本語BM25対応計画書 (PLAN.md)

現在、BM25（およびDense ∪ BM25のハイブリッド検索）はトークン分割（トークナイズ）が英語用にハードコードされており、日本語の評価実行時にはエラーが出力されて制限されています。本計画書では、日本語環境における形態素解析を導入し、BM25を日本語対応させるための具体的な実装方針および手順を定義します。

---

## 1. 目的と現状の課題

- **課題**: 
  - `bm25.py` の `tokenize` 関数は英語の正規表現 `[a-z0-9]+` と英語ストップワードのみに対応しており、日本語テキストを入力するとトークンが一切抽出されません。
  - `bm25.py`、`hybrid.py`、`answer_hybrid.py` にて `lang != "en"` の場合にエラーで終了する制限がかけられています。
  - `Makefile` において、`hybrid` 評価パイプライン（`hybrid-judge`）が英語（`LANG=en`）のみに制限されています。
- **目標**:
  - 日本語環境でもBM25によるキーワード検索および、Dense ∪ BM25によるハイブリッド検索パイプラインが実行可能になり、日本語のQA精度（現在は Vector k=10 の **0.890** が最高実用値）を英語（Hybrid k=10 で **0.960**）と同様に引き上げることを目指します。

---

## 2. 提案アプローチ（日本語トークナイザーの実装）

すでにプロジェクト環境（`pyproject.toml`）に導入されている **spaCy** および日本語モデル **`ja_core_news_sm`** を利用して形態素解析を行います。

### 2.1. 形態素解析とフィルタリング
日本語のBM25スコアリングを効果的に機能させるため、単なる分かち書きだけでなく、検索ノイズとなる助詞や記号などを除外し、意味のある語（キーワード）を抽出します。
- **品詞（POS）フィルターの適用**:
  - spaCyの品詞タグを利用し、**名詞（NOUN, PROPN）**、**動詞（VERB）**、**形容詞（ADJ）**、**副詞（ADV）** のみをトークンとして抽出します。これにより、助詞「の」「に」「は」や補助記号「。」「、」などが自然に除外され、BM25のスパースベクトルの精度が向上します。
- **ストップワード除外**:
  - `remove_stop` が指定された場合、必要に応じて spaCy の `token.is_stop` を利用するか、一般的な日本語ストップワード（一文字の平仮名など）を定義して除外します。

---

## 3. 具体的な実装手順

### ステップ 1: `bm25.py` の修正
1. **spaCy のインポートとロード（遅延ロード）**:
   英語の実行時には spaCy のインポートおよびロードのオーバーヘッドを避けるため、`lang == "ja"` が初めて指定された時点でロードする仕組み（遅延ロード）を実装します。
   ```python
   _nlp_ja = None

   def get_nlp_ja():
       global _nlp_ja
       if _nlp_ja is None:
           import spacy
           _nlp_ja = spacy.load("ja_core_news_sm")
       return _nlp_ja
   ```

2. **`tokenize` 関数の更新**:
   `lang == "ja"` の処理を追加します。
   ```python
   def tokenize(text: str, lang: str = "en", remove_stop: bool = True) -> list[str]:
       if lang == "ja":
           nlp = get_nlp_ja()
           doc = nlp(text)
           # 名詞・動詞・形容詞・副詞を抽出（小文字化も適用）
           allowed_pos = {"NOUN", "PROPN", "VERB", "ADJ", "ADV"}
           tokens = [t.text.lower() for t in doc if t.pos_ in allowed_pos]
           if remove_stop:
               # 日本語ストップワードの簡易フィルタ（必要に応じて）
               tokens = [t for t in tokens if not t.isspace()]
           return tokens
       elif lang == "en":
           # 既存 of 英語用トークナイズロジック
           ...
       else:
           raise NotImplementedError(f"Unsupported language: {lang}")
   ```

3. **`bm25.py` 起動時の制限解除**:
   `main()` 関数内にある `lang != "en"` のチェックおよびエラー出力を除去します。

### ステップ 2: `answer_hybrid.py` の修正
1. **起動時の制限解除**:
   `main()` 関数内の以下の箇所を修正し、`lang == "ja"` を許容します。
   ```python
   # 修正前
   if lang != "en":
       raise SystemExit("answer_hybrid.py: lang=... not supported ...")
   ```
2. **トークナイズ引数の伝播**:
   シーンテキストおよび質問文をトークナイズする箇所で、正しく `lang=lang` を引数に渡すよう確認・修正します。
   - `docs = [tokenize(f"{s['title']} {s['text']}", lang=lang) for s in scenes]`

### ステップ 3: `hybrid.py` の修正
1. **起動時の制限解除**:
   `main()` 関数内の `lang != "en"` によるチェックを除去します。
2. **トークナイズ引数の伝播**:
   `bm25.py` と同様に `lang=lang` がトークナイズ呼び出しへ正しく渡されていることを確認します。

### ステップ 4: `Makefile` の修正
1. **評価パイプラインの有効化**:
   `judge` ターゲット定義時に、`LANG=ja` の場合でも `hybrid` 評価結果（`judge-hybrid5.jsonl`, `judge-hybrid10.jsonl` など）を集計対象に含めるように変更します。
   ```makefile
   # 修正前
   ifeq ($(LANG),en)
   JUDGE_FILES += $(RESULTS)/judge-hybrid5.jsonl $(RESULTS)/judge-hybrid10.jsonl
   ...
   endif

   # 修正後（LANG=jaでもhybridの結果があれば拾い上げる、もしくはLANGの制限を解除）
   # hybridのjudgeファイルは結果があれば自動で集計に加わるようにワイルドカードパターンを追加します。
   JUDGE_FILES += $(patsubst $(RESULTS)/%.jsonl,$(RESULTS)/judge-%.jsonl,$(wildcard $(RESULTS)/hybrid*.jsonl))
   ```
2. **`hybrid` ターゲットの説明コメントの更新**:
   英語限定という記述を更新します。

---

## 4. 動作確認・評価プラン

変更後、以下の手順で動作確認と評価を実施します。

1. **日本語BM25単体の精度評価**
   ```bash
   make LANG=ja bm25
   ```
   - 実行結果から、日本語の各シーンに対するBM25検索のゴールドチャプター・カバレッジ（coverage@k）を確認します。
2. **日本語ハイブリッドQAの実行と評価**
   ```bash
   make LANG=ja hybrid-judge
   ```
   - `results-ja/hybrid5.jsonl` および `results-ja/hybrid10.jsonl` が生成され、Gemini裁判官（`judge.py`）による採点が正常に行われることを確認します。
3. **総合レポートの作成**
   ```bash
   make LANG=ja report
   ```
   - 出力される比較表に `Hybrid k=5` および `Hybrid k=10` の行が追加され、精度（correct/50）が表示されることを確認します。
   - 純粋な dense vector (Vector k=10 の 0.890) に対する精度向上度合いを検証します。
