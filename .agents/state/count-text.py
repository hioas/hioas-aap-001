# -*- coding: utf-8 -*-
"""量设计稿里关键文本的长度（用于字符计数类控件的真值核对）。"""
import sys

texts = sys.argv[1:]
for t in texts:
    print(len(t), repr(t))
