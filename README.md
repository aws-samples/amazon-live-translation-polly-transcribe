### Pre-requisites:

1. Python 3.7.9 
2. Windows machine 
3. Zoom Interpreter Client
4. Properly configured AWS IAM user with these AWS managed polices:
    - AWSCodeCommitPowerUser
    - TranslateFullAccess
    - AmazonTranscribeFullAccess
    - AmazonPollyFullAccess
5. AWS CLI

5. Run aws confgure incommand prompt to configure the aws cli with the previously mentioned IAM user secret and access keys. When running the python script, the aws python library boto3 will look for these necessary security parameters and authorize/authenticate your aws api calls. 

### Steps to run the bot:

1. Install all the dependencies

```
pip install -r requirements.txt
```

2. Run the language assistant. it will ask you to pick the speaker device (Virtual Audio  Output Cable) to record from. And pick the direction of translation. 1 for English to Chinese and 2 for Chinese to English

```
python3 language_assistant.py
```

### Instrumentation

1. You can see average times on the Command Line outputs.
2. To measure WER and BLEU after a test recording, you can run:

```
Python3 jiwertest.py 
Python3 bleu_score.py

Notes: For security reasons, the code that writes to files for later analysis has been commented out, feel free to uncomment the code after delivery.

Contents of the old files folder can be explained as sort of a 'discovery in process' log of the iterations of the bot and experimentations, we left them for later examination if you so choose. 

```