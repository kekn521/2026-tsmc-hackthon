"""提示詞管理 - 集中管理所有 AI 提示詞"""

# === 系統提示詞 ===
SYSTEM_PROMPT = """你是一個專業的程式碼分析專家 AI Agent。
你的任務是深入分析程式碼庫,並實作你的分析結果

記憶路徑
memory/Plan.md 是你的分析結果
memory/AGENTS.md 是你的記憶
artifacts/ 是你的產出物

你的分析結果需要包含以下內容:
- 程式碼庫結構概覽
- 主要組件和模組
- 架構設計和模式
- 發現的問題和改進建議
- 具體的行動建議

並且採取 TDD 的方式進行分析和實作，先運行基本測試，在進行重構語言的測試撰寫，最後重構完成後運行所有測試
"""

# === 使用者訊息模板 ===
USER_MESSAGE_TEMPLATE = """請分析程式碼庫並將分析結果寫入檔案。

# 程式碼庫路徑
{repo_path}

# 分析需求
{init_prompt}

# 任務要求
1. 使用 ls 和 read_file 工具深入探索和分析 {repo_path} 目錄中的程式碼
2. 根據用戶需求進行針對性分析
3. 將分析結果寫入 Markdown 檔案
4. **重要**: 使用 write_file 工具,將結果寫入完整路徑 {artifacts_path}/plan.md

注意:
- 必須使用完整的絕對路徑 {artifacts_path}/plan.md
- 如果 {artifacts_path} 目錄不存在,請先創建它

分析內容應包括(但不限於):
- 程式碼庫結構概覽
- 主要組件和模組
- 架構設計和模式
- 發現的問題和改進建議
- 具體的行動建議

請開始分析並生成檔案。
"""


# === Prompt 變體 (可擴展) ===
PROMPT_VARIANTS = {
    "default": SYSTEM_PROMPT,
    "verbose": SYSTEM_PROMPT + "\n請提供詳細的分析和大量範例。",
    "concise": SYSTEM_PROMPT + "\n請提供簡潔精煉的分析,聚焦於最關鍵的問題。",
}


def get_system_prompt(variant: str = "default") -> str:
    """取得系統提示詞

    Args:
        variant: 提示詞變體 (default, verbose, concise)

    Returns:
        系統提示詞字串
    """
    return PROMPT_VARIANTS.get(variant, SYSTEM_PROMPT)


def build_user_message(
    repo_path: str,
    artifacts_path: str,
    init_prompt: str
) -> str:
    """構建使用者訊息

    Args:
        repo_path: 程式碼庫路徑
        artifacts_path: 產出物路徑
        init_prompt: 初始提示

    Returns:
        格式化的使用者訊息
    """
    return USER_MESSAGE_TEMPLATE.format(
        repo_path=repo_path,
        artifacts_path=artifacts_path,
        init_prompt=init_prompt
    )

