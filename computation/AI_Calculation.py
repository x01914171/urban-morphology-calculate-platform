import numpy as np
import pylandstats
from pylandstats import Landscape
import pandas as pd
import warnings


class AI(Landscape):
    def __init__(self, landscape, **kwargs):
        super().__init__(landscape, **kwargs)

    # 用于计算每种类型公共边的数量
    def get_share_edge(self, class_):
        # 1.将数据转换为二值型
        binary_data = (self.landscape_arr == class_).astype(np.int8)
        # 2.设置卷积模板
        cov_template = np.array([[0, 0, 0],
                                 [0, 0, 1],
                                 [0, 1, 0]])
        # 3.填充边缘
        binary_pad = np.pad(binary_data, 1, mode='constant', constant_values=0)
        # 4.计算公共边总数
        row_num, col_num = binary_pad.shape
        count = 0
        for i in range(1, row_num - 1):
            for j in range(1, col_num - 1):
                if binary_pad[i, j] == 1:
                    count += np.sum(binary_pad[i - 1:i + 2, j - 1:j + 2] * cov_template)
        return count

    # 计算eii
    @property
    def eii(self):
        return pd.Series([self.get_share_edge(class_) for class_ in self.classes], index=self.classes, dtype='float64')

    # 计算最大的eii
    @property
    def max_eii(self):
        arr = self.landscape_arr
        flat_arr = arr.ravel()
        # 规避nodata值
        if self.nodata in flat_arr:
            a_ser = pd.value_counts(flat_arr).drop(self.nodata).reindex(self.classes)
        else:
            a_ser = pd.value_counts(flat_arr).reindex(self.classes)
        n_ser = np.floor(np.sqrt(a_ser))
        m_ser = a_ser - np.square(n_ser)
        max_eii = pd.Series(index=a_ser.index, dtype='float64')
        for i in a_ser.index:
            if m_ser[i] == 0:
                max_eii[i] = (2 * n_ser[i]) * (n_ser[i] - 1)

            elif m_ser[i] <= n_ser[i]:
                max_eii[i] = 2 * n_ser[i] * (n_ser[i] - 1) + 2 * m_ser[i] - 1

            elif m_ser[i] >= n_ser[i]:
                max_eii[i] = 2 * n_ser[i] * (n_ser[i] - 1) + 2 * m_ser[i] - 2

        return max_eii

    # 计算AI指数
    def aggregation_index(self, class_val=None):
        """
        计算斑块类型的聚集指数AI
        :param class_val: 整型，需要计算AI的斑块类型代号
        :return: 标量数值或者Series
        """
        if len(self.classes) < 1:
            # 先注释了，避免一直输出降低速度
            # warnings.warn("当前数组全是空值，没有需要计算的类型聚集指数",
            #               RuntimeWarning,
            #               )
            return np.nan
        if class_val is None:
            return (self.eii / self.max_eii) * 100
        else:
            return ((self.eii / self.max_eii) * 100)[class_val]
