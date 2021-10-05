# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
# Licensed under the Amazon Software License  http://aws.amazon.com/asl/

import nltk
import jieba

with open("translate_pt_tok.txt", "r", encoding="utf-8") as f:
    content = f.read()

hypothesis = [x for x in jieba.cut_for_search(content)]

with open("translate_gt_tok.txt", "r", encoding="utf-8") as f:
    content = f.read()

reference = [x for x in jieba.cut_for_search(content)]

print(len(hypothesis))
print(len(reference))

BLEUscore = nltk.translate.bleu_score.sentence_bleu([reference], hypothesis)
print(BLEUscore)
