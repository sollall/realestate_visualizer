"""extract/mansionreview.pyのスクレイピングが、HTML構造の変化を
サイレントな空データや不明瞭な例外ではなく、原因の分かる例外として
検知できることを確認するテスト。実サイトへのアクセスは行わない。
"""

from datetime import datetime

import pytest

import extract.mansionreview as mansionreview


class FakeResponse:
    """requests.get()の戻り値の代わりに使うダミーレスポンス"""

    def __init__(self, html):
        self.content = html


VALID_BUKKEN_HTML = """
<li class="property-detail-list-item">
  <h2 class="property-detail-content__head-title">テストマンション</h2>
  <table class="property-detail-content_main">
    <tr><td>東京都テスト区1-1-1</td><td>x</td><td>1990年3月</td><td>10階建</td><td>50戸</td></tr>
  </table>
  <table class="property-detail-content_sub">
    <tr><td>a</td><td>b</td><td>c</td><td>d</td><td>e</td><td>f</td></tr>
  </table>
  <table class="recommendTable">
    <tr><th>header</th></tr>
    <tr>
      <td>x</td><td>x</td><td>3000万円</td><td>100万円</td><td>70.00m&#178;</td>
      <td>3LDK</td><td>5階</td><td>南</td><td>相応</td>
    </tr>
  </table>
</li>
"""


def _page_html(bukken_html=""):
    return f"<html><body><ul>{bukken_html}</ul></body></html>"


def test_scrap_from_search_raises_when_no_listing_items(monkeypatch):
    monkeypatch.setattr(mansionreview, "load_page", lambda url: FakeResponse(_page_html()))

    with pytest.raises(mansionreview.MansionReviewScrapeError, match="property-detail-list-item"):
        mansionreview.scrap_from_search("http://example.com")


def test_scrap_from_search_raises_when_required_element_missing(monkeypatch):
    broken_html = """
    <li class="property-detail-list-item">
      <table class="property-detail-content_main"><tr><td>x</td></tr></table>
    </li>
    """
    monkeypatch.setattr(mansionreview, "load_page", lambda url: FakeResponse(_page_html(broken_html)))

    with pytest.raises(mansionreview.MansionReviewScrapeError, match="property-detail-content__head-title"):
        mansionreview.scrap_from_search("http://example.com")


def test_scrap_from_search_parses_valid_html(monkeypatch):
    monkeypatch.setattr(mansionreview, "load_page", lambda url: FakeResponse(_page_html(VALID_BUKKEN_HTML)))

    results = mansionreview.scrap_from_search("http://example.com")

    assert len(results) == 1
    name, price, address, age, area = results[0][:5]
    assert name == "テストマンション"
    assert price == 3000
    assert address == "東京都テスト区1-1-1"
    assert area == 70.0

    expected_age = (datetime.now().year - 1990) + (datetime.now().month - 3) / 12
    assert age == pytest.approx(expected_age)


REAL_STRUCTURE_BUKKEN_HTML = """
<li class="property-detail-list-item">
  <h2 class="property-detail-content__head-title">テストマンション</h2>
  <table class="property-detail-content_main">
    <tr><td>東京都テスト区1-1-1</td><td>x</td><td>1990年3月</td><td>10階建</td><td>50戸</td></tr>
  </table>
  <table class="property-detail-content_sub">
    <tr><td>a</td><td>b</td><td>c</td><td>d</td><td>e</td><td>f</td></tr>
  </table>
  <table class="recommendTable">
    <tr><th>header</th></tr>
    <tr><td>全件を表示する</td></tr>
    <tr>
      <td></td><td>高資産価値・割安新着テストマンション</td><td>20,000万円台</td>
      <td>無料会員登録でモザイクを消す</td><td>1,729万円割安</td><td>情報取得日:2026年08月30日</td>
    </tr>
    <tr>
      <td></td><td>新着リノベorリフォーム済みテストマンション</td><td>43,000万円</td><td>1,890.5万円</td>
      <td>75.19m&#178;</td><td>3LDK</td><td>7階</td><td>北東</td><td>相応</td>
      <td>情報取得日:2026年09月01日</td>
    </tr>
  </table>
</li>
"""


def test_scrap_from_search_skips_non_data_rows_and_uses_leading_9_columns(monkeypatch):
    """「全件を表示する」ボタン行(1列)・未登録会員向けモザイク行(6列)はスキップし、
    末尾に「情報取得日」列が増えた通常データ行(10列)は先頭9列を使って正しくパースできること"""
    monkeypatch.setattr(mansionreview, "load_page", lambda url: FakeResponse(_page_html(REAL_STRUCTURE_BUKKEN_HTML)))

    results = mansionreview.scrap_from_search("http://example.com")

    assert len(results) == 1
    name, price, address, age, area, tsubo_tanka, room_type, num_floor, dire, eva = results[0][:10]
    assert price == 43000
    assert area == 75.19
    assert room_type == "3LDK"
    assert num_floor == "7階"
    assert dire == "北東"
    assert eva == 0


def test_scrap_estate_data_raises_when_pagination_missing(monkeypatch):
    monkeypatch.setattr(mansionreview, "load_page", lambda url: FakeResponse(_page_html()))

    with pytest.raises(mansionreview.MansionReviewScrapeError, match="c-pagination-list__item"):
        mansionreview.scrap_estate_data()
