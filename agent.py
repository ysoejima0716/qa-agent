import os
import anthropic

client = anthropic.Anthropic()

tools = [
    {
        "name": "read_file",
        "description": "ファイルの内容を読み込む",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "読み込むファイルのパス"}
            },
            "required": ["path"],
        },
    },
    {
        "name": "list_files",
        "description": "指定ディレクトリのファイル一覧を取得する",
        "input_schema": {
            "type": "object",
            "properties": {
                "directory": {"type": "string", "description": "ディレクトリのパス（省略時はカレント）"}
            },
        },
    },
]


def run_tool(name, inputs):
    if name == "read_file":
        path = inputs["path"]
        if not os.path.exists(path):
            return f"エラー: ファイルが見つかりません: {path}"
        with open(path, encoding="utf-8", errors="replace") as f:
            content = f.read()
        if len(content) > 10000:
            content = content[:10000] + "\n...(省略)"
        return content

    if name == "list_files":
        directory = inputs.get("directory", ".")
        if not os.path.exists(directory):
            return f"エラー: ディレクトリが見つかりません: {directory}"
        files = os.listdir(directory)
        return "\n".join(sorted(files))

    return f"不明なツール: {name}"


def ask(question, history):
    history.append({"role": "user", "content": question})

    while True:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system="あなたはファイルを読んで質問に答えるQ&Aエージェントです。必要に応じてツールを使ってファイルを参照してください。日本語で回答してください。",
            tools=tools,
            messages=history,
        )

        if response.stop_reason == "end_turn":
            answer = next(b.text for b in response.content if hasattr(b, "text"))
            history.append({"role": "assistant", "content": response.content})
            return answer

        # ツール呼び出し処理
        history.append({"role": "assistant", "content": response.content})
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                result = run_tool(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })
        history.append({"role": "user", "content": tool_results})


def main():
    print("Q&Aエージェント起動 (終了: quit)")
    print("例: 「agent.pyの内容を説明して」「カレントディレクトリのファイル一覧を教えて」")
    print("-" * 50)
    history = []
    while True:
        question = input("\n質問: ").strip()
        if not question:
            continue
        if question.lower() in ("quit", "exit", "q"):
            break
        print("\n回答: ", end="", flush=True)
        answer = ask(question, history)
        print(answer)


if __name__ == "__main__":
    main()
