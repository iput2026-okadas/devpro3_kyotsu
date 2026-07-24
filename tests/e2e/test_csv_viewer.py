import json
import re

from playwright.sync_api import Page, expect


LATEST_FILE = "data-20260102000000.csv"
OLDER_FILE = "data-20260101000000.csv"


def _column_values(page: Page, position: int) -> list[str]:
    return page.locator(
        f"#table-body tr td:nth-child({position})"
    ).all_text_contents()


def test_latest_csv_is_selected_and_rendered(page: Page, base_url: str) -> None:
    page.goto(base_url)

    expect(page).to_have_title(re.compile(LATEST_FILE))
    expect(page.locator(".file-list a")).to_have_count(2)
    expect(page.locator(".file-list a.active")).to_have_text(LATEST_FILE)
    expect(page.locator("#table-header th")).to_have_count(7)
    expect(page.locator("#table-body tr")).to_have_count(3)
    expect(page.locator("#stats")).to_have_text("表示中: 3 / 全 3 件")
    assert _column_values(page, 2) == ["raspi-office", "raspi-lab", "raspi-office"]


def test_csv_file_can_be_switched(page: Page, base_url: str) -> None:
    page.goto(base_url)
    page.get_by_role("link", name=OLDER_FILE).click()

    expect(page).to_have_url(re.compile(rf"\?file={re.escape(OLDER_FILE)}$"))
    expect(page.locator(".file-list a.active")).to_have_text(OLDER_FILE)
    expect(page.locator("#table-body tr")).to_have_count(2)
    assert _column_values(page, 1) == ["101", "102"]


def test_average_values_follow_selected_csv(page: Page, base_url: str) -> None:
    page.goto(base_url)
    temperature_card = page.get_by_text("平均温度", exact=True).locator("..")
    humidity_card = page.get_by_text("平均湿度", exact=True).locator("..")

    expect(temperature_card).to_contain_text("19.8 ℃")
    expect(humidity_card).to_contain_text("47.8 %")

    page.get_by_role("link", name=OLDER_FILE).click()

    expect(temperature_card).to_contain_text("22.8 ℃")
    expect(humidity_card).to_contain_text("45.8 %")


def test_numeric_column_can_be_sorted(page: Page, base_url: str) -> None:
    page.goto(base_url)
    temperature_header = page.locator('th[data-col="temp"]')

    temperature_header.click()
    assert _column_values(page, 4) == ["8.0", "21.5", "30.0"]
    expect(temperature_header.locator(".sort-icon")).to_have_text("▲")

    temperature_header.click()
    assert _column_values(page, 4) == ["30.0", "21.5", "8.0"]
    expect(temperature_header.locator(".sort-icon")).to_have_text("▼")


def test_csv_and_json_can_be_exported(page: Page, base_url: str) -> None:
    page.goto(base_url)

    with page.expect_download() as csv_download_info:
        page.get_by_role("button", name="CSVをエクスポート").click()
    csv_download = csv_download_info.value
    assert csv_download.suggested_filename == LATEST_FILE
    csv_text = csv_download.path().read_text(encoding="utf-8")
    assert csv_text.splitlines()[0] == (
        '"id","client_id","timestamp","temp","humid","co2","light_percent"'
    )
    assert len(csv_text.splitlines()) == 4

    with page.expect_download() as json_download_info:
        page.get_by_role("button", name="JSONをエクスポート").click()
    json_download = json_download_info.value
    assert json_download.suggested_filename == LATEST_FILE.replace(".csv", ".json")
    exported_rows = json.loads(json_download.path().read_text(encoding="utf-8"))
    assert [row["id"] for row in exported_rows] == ["201", "202", "203"]
    assert [row["client_id"] for row in exported_rows] == [
        "raspi-office",
        "raspi-lab",
        "raspi-office",
    ]


def test_missing_csv_shows_an_error(page: Page, base_url: str) -> None:
    page.goto(f"{base_url}/?file=missing.csv")

    expect(page.locator(".error-msg")).to_contain_text(
        "missing.csv が見つかりません"
    )
    expect(page.locator("#table-body tr")).to_have_count(0)


def test_ai_chat_sends_selected_csv_and_displays_response(
    page: Page,
    base_url: str,
) -> None:
    captured_request = {}

    def handle_chat(route) -> None:
        captured_request.update(route.request.post_data_json)
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "response": "直近3件では温度差が22℃あります。",
                    "selected_file": LATEST_FILE,
                }
            ),
        )

    page.route("**/api/chat", handle_chat)
    page.goto(base_url)
    page.get_by_role("button", name="AI分析").click()

    expect(page.get_by_role("dialog", name="CSV分析チャット")).to_be_visible()
    page.get_by_label("CSVについての質問").fill("温度変化を教えて")
    page.get_by_role("button", name="送信").click()

    expect(page.locator(".chat-message.user .chat-message-bubble")).to_have_text(
        "温度変化を教えて"
    )
    expect(
        page.locator(".chat-message.assistant .chat-message-bubble").last
    ).to_have_text("直近3件では温度差が22℃あります。")
    assert captured_request["message"] == "温度変化を教えて"
    assert captured_request["file"] == LATEST_FILE

    page.get_by_role("button", name="履歴削除").click()
    expect(page.locator(".chat-message")).to_have_count(1)
    expect(page.locator(".chat-message-bubble")).to_have_text(
        "会話履歴を削除しました。"
    )
