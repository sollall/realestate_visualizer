from abc import ABC, abstractmethod


class Pipeline(ABC):
    """extract/transformを行うパイプラインの基底クラス"""

    @abstractmethod
    def extract(self):
        raise NotImplementedError

    @abstractmethod
    def transform(self, data):
        raise NotImplementedError
