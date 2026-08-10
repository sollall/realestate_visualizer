from abc import ABC, abstractmethod


class BaseSite(ABC):
    """不動産サイトごとのスクレイピング処理の基底クラス"""

    name: str

    @abstractmethod
    def extract(self):
        """サイトから物件データを取得し、DataFrameを返す"""
        raise NotImplementedError

    @abstractmethod
    def transform(self, data):
        """取得したデータを整形して返す"""
        raise NotImplementedError
