# QA 評価 (Evaluation)

ローカルLLMを用いた小説『*Bou-Thakuranir Haat*』翻訳版に対するQA（質問応答）精度の評価ツール群です。ここでは、回答生成モデルに渡すチャプターの検索手法として、**Vector RAG** を基準とし、チャプター単位の検索戦略である **Extraction**（要約ベース）と **Filter**（yes/maybe/noの関連性判定）の2つを比較しています。さらに、完璧な検索結果の上限値（LLMの読解力のみを純粋に測る基準）として、正解チャプターを直接コンテキストとして与える **Ceiling** ランを実施しています。

検索の基本単位は、段落やチャプター全体ではなく、**シーン（segment）** です。

## 結果 (Results)

各言語で50問の質問を用意し、Geminiで生成した全文ベースの正解（ゴールドスタンダード）を基準に `ollama:qwen3.6` を用いて判定しました。以下の表は、50問中の正答数と、括弧内に加重スコア `(正答数 + 0.5 × 部分正答) / 50` を示しています。**Vector** (`k=5`/`k=10`)、**Vector-line**、**V-hybrid**、**Filter2**、**Filter3**、および **Ceiling** は両言語で実行されています。**Hybrid** は英語のみの実行です（BM25のトークナイズが英語専用であるため）。

| 手法 (Method) | 英語 (English) | 日本語 (Japanese) | 概要 (Description) |
| --- | --- | --- | --- |
| Vector k=5 | 39/50 (0.830) | 38/50 (0.810) | 標準的な密ベクトル検索 (k=5) |
| Vector k=10 | 44/50 (0.920) | 42/50 (0.890) | 標準的な密ベクトル検索 (k=10) |
| Vector-line k=5 | 35/50 (0.800) | 35/50 (0.790) | 行レベルの密ベクトル検索 (k=5) |
| Vector-line k=10 | 41/50 (0.890) | 40/50 (0.840) | 行レベルの密ベクトル検索 (k=10) |
| V-hybrid k=5 | 40/50 (0.890) | 42/50 (0.890) | Segment ∪ Line 密ベクトル集合和 (k=5) |
| V-hybrid k=10 | 43/50 (0.910) | 42/50 (0.880) | Segment ∪ Line 密ベクトル集合和 (k=10) |
| Hybrid k=5 | 43/50 (0.910) | — | Dense ∪ BM25 集合和 (k=5) |
| Hybrid k=10 | 47/50 (0.960) | — | Dense ∪ BM25 集合和 (k=10) |
| Extract | 39/50 (0.830) | 40/50 (0.850) | チャプターごとの要約ベース判定 |
| Filter2 | 36/50 (0.790) | 39/50 (0.820) | LLM-as-retriever (二値判定: yes/no) |
| Filter3 | 45/50 (0.930) | 43/50 (0.880) | LLM-as-retriever (三値判定: yes/maybe/no) |
| Ceiling | 49/50 (0.990) | 47/50 (0.970) | 完璧な検索の上限値 (正解チャプターを直接入力) |
| GraphRAG local | 28/50 (0.660) | — | Microsoft GraphRAG (ローカルエンティティ検索) |
| GraphRAG global | 5/50 (0.170) | — | Microsoft GraphRAG (グローバルコミュニティ検索) |

これらの結果を出力するパイプライン（インデックス構築、各質問への回答、採点、集計）は以下の通りです（Filter と Ceiling はオプトインです）：

- `build_index.py` — シーンの埋め込みインデックス作成 → `index-<lang>.safetensors`
- `answer_vector.py` — Vector k=5/10、Vector-line (`--line`)、および V-hybrid (`--hybrid`、SegmentとLineの密ベクトル集合和; [VECTOR-HYBRID.md](VECTOR-HYBRID.md) 参照) → `results-<lang>/vector[-line|-hybrid]<k>.jsonl`
- `answer_extract.py` — Extract → `results-<lang>/extract.jsonl`
- `answer_filter.py` — Filter2 / Filter3 (リトリーバーとしてのLLM; [FILTER.md](FILTER.md) 参照) → `results-<lang>/filter{2,3}.jsonl`
- `answer_hybrid.py` — Hybrid k=5/10 (Dense ∪ BM25; [HYBRID.md](HYBRID.md) 参照) → `results-<lang>/hybrid<k>.jsonl`
- `answer_ceiling.py` — Ceiling、正解チャプターをコンテキストとして使用 → `results-<lang>/ceiling.jsonl`
- `judge.py` — ゴールドスタンダードに対するLLMでの回答採点 → `results-<lang>/judge-<stem>.jsonl`
- `report.py` — 精度 + 検索チャプターの比較 + ペアワイズの不一致分析 (ターミナルに表を出力)

`answer.py` は、5つのすべての回答スクリプト（vector / extract / filter / ceiling / hybrid）でインポートされる共有ヘルパー（`LANGS`, `PART_RANGES`, `load_questions`, `load_chapters`, `answer_question`）を保持しています。

両言語ともに、回答モデルには `google:gemma-4-31b-it`、インデックスには `embeddinggemma`、そして判定には同じプロンプトを使用しています。

> [!IMPORTANT]
> **実用的な最適解**
> 英語においては、**Dense ∪ BM25 (Union)** の組み合わせ（`Hybrid k=10`）が **0.960** という最高精度を達成しており、実用上の最適解です。
> 日本語においては、BM25 トークナイザーが英語専用であるため、シンプルな **Vector k=10**（あるいは `V-hybrid k=5`）が **0.890** で実用上の最適解となります。

## 戦略別の主な発見 (Key Findings by Strategy)

### Filter (LLM-as-Retriever) — [FILTER.md](FILTER.md)

各バリアントの保持ルールにおける Filter (LLM-as-retriever) の英語での厳密再現率（strict recall）:

| 手法 (method) | 厳密再現率 (strict recall) |
|---|---:|
| Filter2 (yes を保持) | 30 |
| Filter3 (no 以外を保持) | 44 |
| Filter10 (3以上) | 38 |
| Filter5d (合計5以上) | 50 |

* **実用上の優位性なし:** LLMを用いたフィルタリングは、通常のVector RAGに対するコストに見合いません。
* **粒度と取りこぼしの限界 (Gold floor):** 単一評価軸のバリアント（Filter2/3/10）では、誤った「no」判定により正解チャプターが救済できなくなる「取りこぼし（ゴールドフロア）」が 8〜12% 発生します。複数軸でスコアリングする Filter5d はこれを取り除きますが、1問あたり平均約14チャプターを保持することになり、精度（Precision）が崩壊します。
* **非効率なスケーリング:** 実用的な数値バリアントである Filter10 は、Vector k=10 と同等の再現率（Recall）しか得られないにもかかわらず、1回の埋め込みパス（Vector）に対して、1言語あたり約1,850回のLLMコール（Phase 1）を必要とし、実行時間が数百倍に跳ね上がります。

### Hybrid (Dense + BM25) — [HYBRID.md](HYBRID.md)

Dense ∪ BM25 (HYBRID)、英語での比較:

| 手法 (method) | k=5 | k=10 |
|---|---:|---:|
| Dense | 36 | 42 |
| BM25 | 33 | 41 |
| RRF | 32 | 43 |
| Borda | 33 | 43 |
| CombSUM | 35 | 42 |
| **Union (集合和)** | 40 | **46** |

* **融合（Fuse）は悪手 — 集合和（Union）が最善:** RRF、Borda、CombSUM といったランキング融合アルゴリズムは、拾えたはずの正解を押し出してしまい、k=5 では Dense 単体よりも精度が低下します。独立して取得した Dense と BM25 の top-k を単純な集合和（Union）として組み合わせるアプローチは、パラメータの調整が不要で堅牢であり、最も高い精度（両方の深度で +4 の厳密再現率）を達成しました。
* **Denseの死角のカバー:** BM25 のようなレキシカル一致は、密ベクトル（Dense）検索では順位付けがうまくいかない、固有名詞や特徴的な用語（印章指輪やデリーの皇帝といった Class A の取りこぼし）をほぼすべてカバーします。
* **共通の死角:** 4つのクロスリファレンス問題（Q31、Q32、Q38、Q42）は、どちらの検索手法でもカバーできず残ってしまいます。これらを解決するには、融合手法の改善ではなく、クエリ拡張やマルチクエリといった全く別のアプローチが必要です。

### Segment ∪ Line Dense Hybrid (`V-hybrid`) — [VECTOR-HYBRID.md](VECTOR-HYBRID.md)

Segment ∪ Line (VECTOR-HYBRID), 英語 / 日本語:

| 手法 (method) | en k=5 | en k=10 | ja k=5 | ja k=10 |
|---|---:|---:|---:|---:|
| Segment (= Dense) | 36 | 42 | 36 | **45** |
| Line | 33 | 39 | 31 | 38 |
| Mix | 32 | 36 | 32 | 38 |
| **Union (集合和)** | 38 | **45** | 41 | **45** |

* **異なる粒度の集合和:** セグメントレベルと行レベルの密ベクトル検索結果の集合和をとることで、厳密再現率（strict recall）が向上します。行レベルの検索は特徴的な1行を見つけ出すのに優れており、セグメントレベルの検索は広がりのある文脈を捉えるのに優れています。
* **コンテキスト量とのトレードオフ:** ただし、コンテキストのバジェット（文章量）を同一に揃えた場合（V-hybrid k=5 vs Vector k=10）、V-hybrid が単一インデックスの通常の Vector検索を上回ることはありません。検索精度の向上分が、コンテキストの拡大による「lost in the middle（中間情報の喪失）」ペナルティによって相殺されてしまうためです。

### Case Studies & Language Comparison — [results-en/README.md](results-en/README.md) & [results-ja/README.md](results-ja/README.md)

* **課題はリトリーバル（検索）にあり:** シングルパッセージの質問はほぼ完璧に解けます。残された難題は完全にクロスリファレンスの質問（複数チャプターにまたがるもの）に集中しています。
* **Ceiling の実証:** Ceiling ラン（正解チャプターをそのまま渡す）では 0.990 (英語) と 0.970 (日本語) のスコアを達成し、適切なコンテキストさえ与えられれば LLM の読解力はほぼ完璧であることが証明されました。Q48 のみが唯一の読解限界（synthesis floor）として残りました。
* **Extract の失敗原因:** Extract 手法での失点は、回答生成時の失敗ではなく、そのほとんどが Phase 1 の偽陰性（False negative: 要約が正解チャプターを切り捨ててしまうこと）によるものです。
* **言語による差異なし:** 使用する言語は精度にほとんど影響を与えません（英語と日本語の総計スコアの差は1〜2問に収まっています）。同じ埋め込みモデルを使用しているため、検索で取りこぼす箇所も同一です。

### GraphRAG — [graphrag/README.md](graphrag/README.md)

* **回答生成の崩壊:** GraphRAG の `local` 検索 (0.660) は単純なベクトル検索を下回りました。再現率（Recall 0.860）は高いものの、適合率（Precision）が 0.135 と崩壊しており、コンテキストにノイズが溢れて回答生成の失敗（synthesis failure）を引き起こしました。
* **構造的強み:** エンティティの関係性を示す質問（Q26/Q28）に対しては、パッセージのコンテキストがゼロでも完璧に回答でき、またグラフの探索を通じて Class A の質問を自己解決できる強みがあります。
* **Global検索の失敗:** `global` でのコミュニティサマリー検索は抽象度が高すぎるため、パッセージレベルの詳細を問うQAには全く機能しません（0.170）。
* **極端なコスト:** グラフの構築およびクエリの実行に13時間以上を要し、数分で済む単純なベクトルインデックス化と比較して実用性に乏しいです。

## 総括とプラクティカルな結論 (Overall Conclusions and Practical Takeaways)

1. **評価軸はリトリーバルに集約される:** `Ceiling` の結果が示す通り、回答生成用のコンテキスト内に「正解のチャプター」が過不足なく含まれてさえいれば、モデルは高い精度で回答を生成できます。したがって、QAシステムの改善はリトリーバル（検索）の再現率向上にほぼ完全に等しいと言えます。
2. **融合（Fuse）ではなく集合和（Union）を:** 異なるリトリーバー（DenseとBM25、あるいはSegmentとLineなど）の結果を統合する際、スコアをブレンドして単一のランキングを作る手法（RRFなど）は、かえって正解を押し出してしまう結果になります。個別に取得した top-k の単純な「集合和」をとることが、最も安全かつ最大の効果を得られるアプローチです。
3. **英語と日本語の最適戦略の分岐:**
   * **英語:** `Hybrid k=10` (Dense ∪ BM25 Union) が 0.960 を記録し、最善のアプローチです。単一の密ベクトル検索の限界を効果的に打破し、Ceiling に最も近づきました。
   * **日本語:** BM25 によるスパースマッチングが利用できないため、よりシンプルな **Vector k=10** (0.890) が最適解となります。バジェット（コンテキスト量）を同一にした場合、`V-hybrid` のような複雑な手法を用いても、単純な `Vector k=10` を上回ることはありません。

## パイプライン (`Makefile`)

ビルドパイプラインは `Makefile` 経由で繋がっています。詳細なターゲットの説明、使い方、オプション（`LANG`、`LINE`、`K` など）、およびオプトインの戦略については、[Makefile](Makefile) のコメントを直接参照してください。

## 対象外 (Out of scope)

以下の方向性は意図的に追求していません（これらの境界線の背後にある分析については [HYBRID.md](HYBRID.md) および [FILTER.md](FILTER.md) を参照してください）：

- **クラウドモデルを用いた全文コンテキスト入力（Whole-text-in-context）のベースライン検証。**
- **4つの共通の死角を開拓すること**（Q31 Ch22、Q32 Ch15、Q38 Ch32、Q42 Ch23 — Dense と BM25 の両方が top-10 圏外に落としてしまう正解チャプター。[HYBRID.md § Shared blind spots](HYBRID.md#shared-blind-spots) 参照）。2つのリトリーバーをどれだけうまくブレンドしてもこれらには到達できません。これらを開拓するには、より良いブレンドではなく、全く異なる検索メカニズム（クエリ拡張やマルチクエリなど）が必要です。5軸の Filter はこれらを浮上させますが、適合率が低すぎる（0.120）ため非実用的です（[FILTER.md](FILTER.md)）。

## `ref/`

リファレンス資料として保持されていますが、パイプラインの一部ではありません。

- [ref/example.py](ref/example.py) — ollama の `embed()` API を使用する最小限の実行例で、コメントには EmbeddingGemma プロンプトの規則が記載されています。
