# ultrastronomy: Initial Implementation Mission

作業ディレクトリ:

このリポジトリのルート

あなたには、ultrastronomy という新しいオープンソースプロジェクトの初期設計と実装を依頼します。

単なる設計書ではなく、実際に動作し、第三者が利用・貢献できる最小限のプロダクトを構築してください。

## 1. Vision

ultrastronomy is an open-source harness and skill collection that enables anyone to contribute to astronomical discovery using their spare AI capacity.

かつて SETI@home は、世界中の人々の余剰計算能力を科学的探索に活用しました。

ultrastronomy は、世界中の人々が利用できる余剰 AI Usage Limit と AI エージェントの能力を、天文学的発見のために活用します。

私たちが実現したい体験は次のとおりです。

1. 天文学の知識がない人でも参加できる。
2. 自分が普段使用している AI エージェントで参加できる。
3. 余った AI Usage Limit を使って実際の天文学研究を進められる。
4. AI が可能な限り科学的な間違いを犯さない。
5. AI が何をすべきか迷わず、適切な研究手順を実行できる。
6. 小さな探索でも具体的な進捗と手応えがある。
7. 結果が科学的に有用であれば、他の参加者や研究者に貢献できる。

## 2. Relationship with Claudestronomy

https://claudestronomy.com/

ultrastronomy は Claudestronomy の理念と科学的方針に賛同します。

競合する研究コミュニティを作ることは目的ではありません。

Claudestronomy に参加する人々も利用できる、オープンで再利用可能なソフトウェア基盤を目指してください。

ただし、ultrastronomy は現時点では独立したプロジェクトです。公式な提携、承認、後援があるかのように表示してはいけません。

Claudestronomy の公開資料を確認し、特に科学的な品質保証方針を設計に取り込んでください。

## 3. Core Philosophy

### Harness: Make agents less wrong

AI エージェントの出力を無条件に信用しないでください。

科学的な正確性は、プロンプトだけでは保証できません。

可能な限り、決定論的なソフトウェア、データ検証、統計的評価、独立した再実行によって担保してください。

特に以下を重視します。

- 観測データと AI が推定した内容の明確な分離
- データの出典と provenance
- 単位、座標系、時刻系、測光系などの整合性
- 既知の天体・既知の現象の再発見
- Synthetic injection による検出感度の評価
- False positive の定量的評価
- Data leakage の防止
- 仮説、閾値、評価条件の事前固定
- 独立した検証
- 再現可能な実験
- Negative results / null results の保存
- 不確実な場合に判断を保留する能力

「AI が発見した」と「科学的に発見が確認された」は、絶対に混同しないでください。

### Skills: Make agents less lost

AI エージェントが天文学研究の各工程で何をすべきか判断できるようにしてください。

Agent Skills の公開仕様を優先してください。

https://agentskills.io/specification

Claude Code、Codex、Gemini CLI、OpenCode などの異なる AI エージェントから利用できる構造を目指します。

ただし、全エージェントの互換性を確認せずに、対応済みと宣言しないでください。

最初から大量のスキルを作らず、実際の探索で必要になるものを厳選してください。

各スキルには以下を含めてください。

- 適用場面
- 前提知識・入力条件
- 実行手順
- 利用可能なツールとデータ
- 成功条件
- 典型的な失敗
- 検証手順
- 実行例

### Experience: Make science accessible and rewarding

参加者に専門知識や高価な計算設備を要求しないでください。

少なくとも一つの簡単な科学的探索を、初心者がローカル環境で開始できるようにしてください。

参加者には次を示します。

- 何を探索しているのか
- なぜその探索に意味があるのか
- どこまで探索が進んだのか
- 何が観測・検出されたのか
- 何が未検証なのか
- 次に何を調べればよいのか
- 自分の成果をどう共有・貢献できるのか

既知天体の再発見、正しく評価された非検出、再現性のある分析も有益な貢献として扱ってください。

科学的に不確かな結果を、娯楽性のために発見として誇張してはいけません。

## 4. Architecture Requirements

以下の方針を採用してください。

- Local-first
- Open source
- Agent-agnostic
- Provider-agnostic
- Reproducible
- Observable
- Testable
- Extensible

中央サーバー、アカウント管理、独自の AI プロバイダー抽象化、分散ジョブスケジューラーは、最初から実装しないでください。

参加者の既存の AI エージェントをそのまま利用することを優先してください。

Usage Limit や契約上のクレジットは、移転・共有できるとは限りません。各プロバイダーの利用規約を守ってください。

API キーやセッショントークンを収集・送信しないでください。

AI の Usage Limit を無制限に消費しないよう、予算上限、停止条件、実行前確認を設計してください。残量取得 API がない環境では、残量を推測して表示しないでください。

科学データについても利用規約、アクセス制限、レート制限を守ってください。

## 5. First Scientific Mission

最初の科学的ユースケースは、公開天文データにおける既知現象の再発見とします。

候補:

- Zwicky Transient Facility (ZTF)
- Fink alert broker
- Historical astronomical transients

https://doc.ztf.fink-broker.org/

ただし、既存の研究・実装を最初に調べてください。

新しいアルゴリズムを開発すること自体を目的にしてはいけません。

まず既知の天体・現象を再現可能な方法で検出し、探索手法が正しく機能することを確認してください。

可能なら、過去の re-science プロジェクトの成果を参照してください。ただし、その存在や場所は仮定せず、利用できる場合だけ調査してください。

## 6. MVP Acceptance Criteria

最初の MVP は、最低限以下を満たしてください。

1. README を読んだ第三者が、自分の AI エージェントで探索を開始できる。
2. 天文学の知識がない AI エージェントでも、スキルに従って作業できる。
3. 小さな公開データセットまたは許諾されたサンプルデータで動作する。
4. オフラインでも再現可能なデモまたはテストがある。
5. 既知の天体・現象を対象にした評価がある。
6. AI が生成した推測と、プログラムが検証した事実を区別できる。
7. 実験条件、データ出典、コード、結果、失敗を記録できる。
8. 結果を別の人間・AI エージェントが再検証できる。
9. 貢献方法が明確で、GitHub で成果を共有できる。
10. 未検証の候補を新発見として発表しない仕組みがある。

実際の未知天体の発見を、MVP の成功条件にしないでください。

## 7. Development Process

以下の順序で実施してください。

### Phase 0: Research

Claudestronomy、Agent Skills、既存の天文学 OSS、公開データ API を調査してください。

既存のファイルがある場合は先に確認してください。

類似プロジェクトとの差分、再利用可能なコンポーネント、実装不要な機能を整理してください。

### Phase 1: Minimal Design

プロジェクトの目的、非目標、アーキテクチャ、科学的品質保証、MVP の完了条件を短く明文化してください。

AGENTS.md をエージェント共通の入口とし、Agent Skills の標準仕様に従ったスキル群を設計してください。

エージェント固有の設定は、必要な場合に限って追加してください。

### Phase 2: Implementation

最初の科学的探索をエンドツーエンドで実行できる最小構成を実装してください。

同じ内容を複数の言語やフレームワークで重複実装しないでください。

### Phase 3: Evaluation

テストを実行してください。

可能なら、独立したエージェントまたは別の検証手順で、成果物の問題点を洗い出してください。

科学的な検証とソフトウェアの動作確認は別々に評価してください。

### Phase 4: Documentation

以下を第三者が理解できるようにしてください。

- What is ultrastronomy?
- Why does it exist?
- How do I start?
- What can my AI agent do?
- How can I contribute?
- How are results validated?
- How does it relate to Claudestronomy?

公開ドキュメントの基本言語は英語とします。

## 8. Engineering Principles

以下を強く意識してください。

1. Question every requirement.
2. Delete unnecessary components.
3. Simplify what remains.
4. Optimize only demonstrated bottlenecks.
5. Automate only well-understood processes.

AI エージェントのための複雑なフレームワークを作ること自体が目的になってはいけません。

研究者や参加者にとって有用な、最小限の実装を追求してください。

不要な機能、抽象化、設定、依存関係、ドキュメントは増やさないでください。

科学的正確性、セキュリティ、再現性を犠牲にした単純化は認めません。

## 9. Definition of Done

完了時には、次を報告してください。

- 実装した内容
- 実際に動作する開始手順
- テストと科学的評価の結果
- 満たした Acceptance Criteria
- 未達成の Acceptance Criteria
- 科学的に未検証の事項
- 既存プロジェクトとの差分
- 次に検証すべき最小の課題

ドキュメントだけを大量生成して完了としないでください。

実行可能な最小の研究体験を優先してください。

このリポジトリを、科学的に誠実で、誰でも参加でき、将来の発見につながる OSS として立ち上げてください。
