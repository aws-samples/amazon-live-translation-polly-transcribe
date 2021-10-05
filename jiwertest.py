# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
# Licensed under the Amazon Software License  http://aws.amazon.com/asl/

import jiwer
import docx
import string

def getText(filename):
    doc = docx.Document(filename)
    fullText = []
    for para in doc.paragraphs:
        fullText.append(para.text)
    return '\n'.join(fullText)


with open("transcribe_gt.txt", "r") as f:
    ground_truth = f.read()

with open("transcribe_pt.txt", "r") as f:
    hypothesis = f.read()


characters = ['.', '?', ',']

new_ground_truth = ground_truth.split()
new_hypothesis = hypothesis.split()

ground_truth = []
hypothesis = []

for w in new_ground_truth:
    ground_truth.append(w.lower().replace(".", "").replace("?", "").replace(",", ""))

for w in new_hypothesis:
    hypothesis.append(w.lower().replace(".", "").replace("?", "").replace(",", ""))

with open("groundtruth.txt", "w") as f:
    f.write(' '.join(ground_truth))

with open("hypothesis.txt", "w") as f:
    f.write(' '.join(hypothesis))

# Create a transformation function to preprocess transcript
transformation = jiwer.Compose([
    jiwer.ToLowerCase(),
    jiwer.RemoveMultipleSpaces(),
    #jiwer.RemovePunctuation(),
    jiwer.RemoveWhiteSpace(replace_by_space=True),
    jiwer.RemoveEmptyStrings(),
    jiwer.SentencesToListOfWords(),
    jiwer.SentencesToListOfWords(word_delimiter=" ")
])

wer = jiwer.wer(ground_truth, hypothesis, 
    truth_transform=transformation, 
    hypothesis_transform=transformation)
mer = jiwer.mer(ground_truth, hypothesis, 
    truth_transform=transformation, 
    hypothesis_transform=transformation)
wil = jiwer.wil(ground_truth, hypothesis, 
    truth_transform=transformation, 
    hypothesis_transform=transformation)

# faster, because `compute_measures` only needs to perform the heavy lifting once:
measures = jiwer.compute_measures(ground_truth, hypothesis)
wer = measures['wer'] * 100
mer = measures['mer'] * 100
wil = measures['wil'] * 100

print(wer,mer,wil)
