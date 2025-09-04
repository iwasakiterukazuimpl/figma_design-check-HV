# Figma Design Check HV

Figma APIとOpenAI GPTを組み合わせて、デザインガイドラインとデザインカンプの差分を自動チェックするツールです。

## 🚀 機能

- **ガイドライン抽出**: デザインガイドライン画像から色とフォントのルールを自動抽出
- **Figma API連携**: Figmaファイルから実際のフォント情報を取得
- **デザイン解析**: デザインカンプ画像から要素を自動抽出
- **差分チェック**: ガイドラインとデザインカンプの差分を自動比較
- **レポート生成**: Markdown形式で差分レポートを出力

## 📋 必要な環境

- Python 3.7+
- OpenAI API キー
- Figma Personal Access Token
- Figma ファイルキー

## 🛠️ セットアップ

### 1. 依存関係のインストール

```bash
pip install openai requests python-dotenv
```

### 2. 環境変数の設定

プロジェクトルートに`.env`ファイルを作成し、以下の内容を設定してください：

```env
OPENAI_API_KEY=your_openai_api_key_here
FIGMA_TOKEN=your_figma_personal_access_token_here
FILE_KEY=your_figma_file_key_here
```

### 3. 必要な画像ファイルの配置

以下の画像ファイルを同じディレクトリに配置してください：

- `guideline.png` - デザインガイドライン画像
- `design.png` - デザインカンプ画像

## 🎯 使用方法

### 基本的な実行

```bash
python 03_check-HV.py
```

### 実行の流れ

1. **Step1**: ガイドライン抽出
   - `guideline.png`から色とフォントのルールを抽出
   - OpenAI GPT-4o-miniを使用

2. **Step2**: Figma API連携
   - 指定されたFigmaファイルからフォント情報を取得
   - テキスト要素のフォントサイズとファミリーを抽出

3. **Step3**: デザインカンプ解析
   - `design.png`からセクションごとの要素を抽出
   - Figma APIの情報を参考に正確なフォント情報を設定

4. **Step4**: 差分チェック
   - ガイドラインとデザインカンプを比較
   - 差分を表形式でレポート出力

## 📁 出力ファイル

- `diff_report_hybrid.md` - 差分チェックレポート（Markdown形式）
- `debug_data.json` - デバッグ用の中間データ

## 🔧 設定項目

### OpenAI API設定
- モデル: `gpt-4o-mini`
- プロンプト: デザイン解析に特化したカスタムプロンプト

### Figma API設定
- エンドポイント: `https://api.figma.com/v1/files/{file_key}`
- 認証: Personal Access Token

## 📊 出力例

### ガイドライン抽出結果
```json
{
  "colors": {
    "textColor": "#333333",
    "buttonTextColor": "#FFFFFF",
    "backgroundColor": "#F5F5F5"
  },
  "fonts": {
    "japaneseFont": "NotoSans JP",
    "englishFont": "Poppins"
  },
  "fontSizes": {
    "h1": "24px",
    "h2": "20px",
    "body": "16px"
  }
}
```

### 差分レポート
- カラー使用の一貫性チェック
- フォントファミリーの準拠確認
- フォントサイズの適切性評価
- 全体的なデザイン一貫性の分析

## ⚠️ 注意事項

- Figma Personal Access Tokenは定期的に期限切れになる場合があります
- 画像ファイルは高解像度で、テキストが読み取りやすいものを使用してください
- OpenAI APIの利用料金が発生します
- Figmaファイルへの適切なアクセス権限が必要です

## 🐛 トラブルシューティング

### よくあるエラー

1. **403 Forbidden**: Figmaトークンの期限切れまたは権限不足
2. **画像ファイルが見つからない**: ファイルパスの確認
3. **OpenAI API エラー**: APIキーの設定確認

### デバッグ方法

- `.env`ファイルの設定値を確認
- Figmaファイルの共有設定を確認
- 画像ファイルの存在確認

## 📝 ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 🤝 コントリビューション

バグレポートや機能要望、プルリクエストを歓迎します！

## 📞 サポート

問題が発生した場合は、GitHubのIssuesページで報告してください。
