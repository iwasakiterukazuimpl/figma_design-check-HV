import os
import base64
import json
import requests
import re
from openai import OpenAI
from dotenv import load_dotenv

# .env ファイルを読み込む
load_dotenv()

# 環境変数から API キーを取得
api_key = os.getenv("OPENAI_API_KEY")
figma_token = os.getenv("FIGMA_TOKEN")
figma_file_key = os.getenv("FILE_KEY")

if not api_key:
    raise ValueError("OPENAI_API_KEY が設定されていません。.env を確認してください。")

if not figma_token or not figma_file_key:
    raise ValueError("FIGMA_TOKEN / FILE_KEY が設定されていません。.env を確認してください。")

# OpenAI クライアントを初期化
client = OpenAI(api_key=api_key)

# -----------------------------
# Utility
# -----------------------------
def encode_image(image_path):
    """画像をbase64エンコード"""
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"画像ファイルが見つかりません: {image_path}")
    
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def extract_json_from_text(text):
    """テキストからJSONを抽出"""
    # JSONブロックを探す
    json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
    else:
        # 波括弧で囲まれた部分を探す
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
        else:
            raise ValueError("JSONが見つかりませんでした")
    
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"JSON解析エラー: {e}")
        print(f"問題のテキスト: {json_str[:200]}...")
        raise

def get_figma_text_styles(file_key, token):
    """Figma APIからテキストノードのフォント情報を取得"""
    url = f"https://api.figma.com/v1/files/{file_key}"
    headers = {"X-Figma-Token": token}
    
    try:
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        print(f"✅ Figma API接続成功: {len(data.get('document', {}).get('children', []))}個のトップレベルノード")
    except requests.exceptions.RequestException as e:
        print(f"❌ Figma API エラー: {e}")
        return {}

    font_info = {}
    def traverse(node):
        if node.get("type") == "TEXT":
            text = node.get("characters", "")
            style = node.get("style", {})
            font_size = style.get("fontSize", "unknown")
            font_family = style.get("fontFamily", "unknown")
            if text and text.strip():  # 空文字でない場合
                font_info[text] = {
                    "fontSize": font_size,
                    "fontFamily": font_family
                }
                print(f"📝 テキスト発見: '{text}' → フォント: {font_family}, サイズ: {font_size}")
        elif node.get("type") == "INSTANCE" or node.get("type") == "COMPONENT":
            # インスタンスやコンポーネント内も探索
            pass
        
        # 子ノードを探索
        for child in node.get("children", []):
            traverse(child)
    
    try:
        traverse(data["document"])
        print(f"📊 総テキスト数: {len(font_info)}")
    except KeyError as e:
        print(f"❌ Figma APIレスポンスエラー: {e}")
        print(f"利用可能なキー: {list(data.keys())}")
        return {}
    
    return font_info

def merge_with_font_sizes(gpt_data, font_map):
    """GPT出力のJSONに、Figmaから取得したfontSizeを補完"""
    if isinstance(gpt_data, str):
        try:
            gpt_data = extract_json_from_text(gpt_data)
        except ValueError:
            print("GPT出力のJSON解析に失敗しました")
            return gpt_data
    
    # セクション構造を想定
    if "sections" in gpt_data:
        for section in gpt_data["sections"]:
            for el in section.get("elements", []):
                if el.get("fontSize") in ("unknown", None):
                    txt = el.get("content", "")
                    if txt in font_map:
                        el["fontSize"] = font_map[txt]
    # 単一の要素配列の場合
    elif isinstance(gpt_data, list):
        for el in gpt_data:
            if el.get("fontSize") in ("unknown", None):
                txt = el.get("content", "")
                if txt in font_map:
                    el["fontSize"] = font_map[txt]
    
    return gpt_data

# -----------------------------
# Step1: GPTでガイドライン抽出
# -----------------------------
print("📋 Step1: ガイドライン抽出中...")
try:
    guideline_img = encode_image("guideline.png")
    guideline_prompt = """
あなたはデザインチェックAIです。
この guideline.png から色とフォントのルールを詳細に抽出し、以下のJSON形式で出力してください。

**重要**: ガイドラインから具体的な用途や意味を読み取り、分かりやすい名前で分類してください。

```json
{
  "colors": {
    "textColor": "#テキストカラー",
    "buttonTextColor": "#ボタン・テキストカラー",
    "textBoxColor": "#テキストボックス色",
    "backgroundColor1": "#背景色1",
    "backgroundColor2": "#背景色2",
    "footerBackgroundColor": "#フッター背景色"
  },
  "fonts": {
    "japaneseFont": "日本語フォント名",
    "englishFont": "英数字フォント名"
  },
  "fontSizes": {
    "h1": "h1フォントサイズ",
    "h2": "h2フォントサイズ",
    "h3": "h3フォントサイズ",
    "body": "本文フォントサイズ"
  }
}
```

**抽出のポイント:**
- 色は用途別に分類（テキスト、ボタン、背景、フッターなど）
- フォントは言語別に分類（日本語、英数字）
- フォントサイズは見出しレベル別に分類
- ガイドラインに明記されている具体的な用途や意味を反映
- 必ずJSONブロックで出力してください
"""
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "あなたはデザイン解析AIです。ガイドラインから具体的な用途や意味を読み取り、分かりやすい名前で分類して必ずJSON形式で出力してください。"},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": guideline_prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{guideline_img}"}},
                ],
            },
        ],
    )
    guideline_json = response.choices[0].message.content
    print("✅ ガイドライン抽出完了")
except Exception as e:
    print(f"❌ ガイドライン抽出エラー: {e}")
    guideline_json = '{"colors": {}, "fonts": {}, "fontSizes": {}}'

# -----------------------------
# Step2: Figma APIからフォント情報を取得
# -----------------------------
print("🔧 Step2: Figma APIからフォント情報取得中...")
try:
    font_info_map = get_figma_text_styles(figma_file_key, figma_token)
    print(f"📊 取得したフォント情報: {len(font_info_map)}件")
    
    if font_info_map:
        # フォント情報を文字列に変換
        font_info = "\n".join([
            f"- テキスト: '{text}' → フォントサイズ: {info['fontSize']}, フォントファミリー: {info['fontFamily']}" 
            for text, info in font_info_map.items()
        ])
    else:
        # フォント情報が取得できない場合のフォールバック
        font_info = """
**注意**: Figma APIからフォント情報を取得できませんでした。
以下の一般的なフォント情報を参考にしてください：

- 日本語テキスト: NotoSans JP (一般的な日本語フォント)
- 英数字テキスト: Poppins (一般的な英数字フォント)
- 見出し: 24px, 20px, 16px (一般的な見出しサイズ)
- 本文: 14px, 16px (一般的な本文サイズ)
- ボタンテキスト: 14px, 16px (一般的なボタンサイズ)
"""
        print("⚠️ フォント情報が取得できませんでした。フォールバック情報を使用します。")
    
except Exception as e:
    print(f"❌ Figma API処理エラー: {e}")
    font_info_map = {}
    font_info = """
**注意**: Figma APIからフォント情報を取得できませんでした。
以下の一般的なフォント情報を参考にしてください：

- 日本語テキスト: NotoSans JP (一般的な日本語フォント)
- 英数字テキスト: Poppins (一般的な英数字フォント)
- 見出し: 24px, 20px, 16px (一般的な見出しサイズ)
- 本文: 14px, 16px (一般的な本文サイズ)
- ボタンテキスト: 14px, 16px (一般的なボタンサイズ)
"""

# -----------------------------
# Step3: GPTでデザインカンプ抽出（Figma API情報付き）
# -----------------------------
print("🎨 Step3: デザインカンプ抽出中...")
try:
    design_img = encode_image("design.png")
    design_prompt = f"""
この design.png からセクションごとに要素を抽出し、以下のJSON形式で出力してください。

**重要**: 以下のFigma APIから取得したフォント情報を参考にして、正確なfontSizeとfontFamilyを設定してください。

### Figma APIから取得したフォント情報:
{font_info}

### 出力形式:
```json
{{
  "sections": [
    {{
      "name": "セクション名",
      "elements": [
        {{
          "type": "要素タイプ",
          "content": "テキスト内容",
          "fontFamily": "具体的なフォント名（例: NotoSans JP, Poppins）",
          "fontSize": "具体的な数値（例: 24, 20, 16, 14）",
          "color": "#色コード"
        }}
      ]
    }}
  ]
}}
```

**注意事項:**
- fontSizeとfontFamilyは必ず具体的な値で出力してください（プレースホルダーやunknownは使用禁止）
- 上記のFigma API情報を参考にして、テキスト内容が一致する場合はそのfontSizeとfontFamilyを使用してください
- テキスト内容が完全に一致しない場合は、以下のルールで推測してください：
  - 日本語テキスト → NotoSans JP
  - 英数字テキスト → Poppins
  - 見出し → 24px, 20px, 16px
  - 本文 → 14px, 16px
  - ボタンテキスト → 14px, 16px
- 必ずJSONブロックで出力してください
"""
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "あなたはデザイン解析AIです。必ずJSON形式で出力してください。"},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": design_prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{design_img}"}},
                ],
            },
        ],
    )
    draft_json = response.choices[0].message.content
    print("✅ デザインカンプ抽出完了")
except Exception as e:
    print(f"❌ デザインカンプ抽出エラー: {e}")
    draft_json = '{"sections": []}'

# -----------------------------
# Step4: GPTに差分チェック依頼
# -----------------------------
print("🔍 Step4: 差分チェック中...")
try:
    compare_prompt = f"""
以下はデザインガイドラインとデザインカンプのJSONです。
両者を比較して、以下の形式で **Markdown** レポートを出力してください。

## ガイドライン
```json
{guideline_json}
```

## デザインカンプ（Figma API情報付き）
```json
{json.dumps(draft_json, ensure_ascii=False, indent=2)}
```

### 出力形式:
```markdown
### 1. ガイドラインからの抽出

#### カラー
- テキストカラー: [色コード]
- ボタン・テキストカラー: [色コード]
- テキストボックス: [色コード]
- 背景色1: [色コード]
- 背景色2: [色コード]
- フッター背景色: [色コード]

#### フォント
- 日本語フォント: **[フォント名]**
- 英数字フォント: **[フォント名]**
- h1 フォントサイズ: [サイズ]px
- h2 フォントサイズ: [サイズ]px
- h3 フォントサイズ: [サイズ]px

---

### 2. デザインからの情報抽出

#### セクション: [セクション名]
- elements:
  - type: [要素タイプ]
    content: [テキスト内容]
    fontFamily: [フォント名]
    fontSize: [フォントサイズ]
    color: [色コード]
  [他の要素も同様に]

---

### 3. 差分の比較

| 要素タイプ | デザイン要素 | ガイドライン | 差分 |
|------------|-------------|-------------|------|
| [要素タイプ] | [デザイン要素] | [ガイドライン] | [差分内容] |

[全体的な評価と改善提案]
```

**チェック観点:**
- 色の使用がガイドラインに準拠しているか
- フォントファミリーがガイドラインに準拠しているか
- フォントサイズがガイドラインに準拠しているか
- 全体的なデザインの一貫性

必ず上記の形式で出力し、表形式で差分を明確に示してください。
"""
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "あなたは厳密なデザイン監査AIです。"},
            {"role": "user", "content": compare_prompt},
        ],
    )

    report = response.choices[0].message.content
    print("✅ 差分チェック完了")
except Exception as e:
    print(f"❌ 差分チェックエラー: {e}")
    report = "# エラーが発生しました\n\n差分チェック中にエラーが発生しました。"

# -----------------------------
# 保存
# -----------------------------
try:
    with open("diff_report_hybrid.md", "w", encoding="utf-8") as f:
        f.write(report)
    print("✅ 差分レポートを diff_report_hybrid.md に保存しました！")
except Exception as e:
    print(f"❌ ファイル保存エラー: {e}")

# デバッグ用：中間結果も保存
try:
    debug_data = {
        "guideline": guideline_json,
        "design_final": draft_json,
        "font_info_map": font_info_map
    }
    with open("debug_data.json", "w", encoding="utf-8") as f:
        json.dump(debug_data, f, ensure_ascii=False, indent=2)
    print("✅ デバッグデータを debug_data.json に保存しました！")
except Exception as e:
    print(f"❌ デバッグデータ保存エラー: {e}")
