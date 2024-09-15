"""
At the command line, only need to run once to install the package via pip:

$ pip install google-generativeai
"""

import sys, os, re, time, common

print("Reading modules...")
import google.generativeai as genai

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    print("Please set GOOGLE_API_KEY environment variable.", file=sys.stderr)
    sys.exit(1)
genai.configure(api_key=GOOGLE_API_KEY)

# Set up the model
generation_config = {
    "temperature": 0.1,
    "top_p": 1,
    "top_k": 1,
    "max_output_tokens": 4096, # 2048
}

safety_settings = [
    {
        "category": "HARM_CATEGORY_HARASSMENT",
        "threshold": "BLOCK_NONE"
    },
    {
        "category": "HARM_CATEGORY_HATE_SPEECH",
        "threshold": "BLOCK_NONE"
    },
    {
        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        "threshold": "BLOCK_NONE"
    },
    {
        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
        "threshold": "BLOCK_NONE"
    }
]

def parse(s, i):
    start = s[i]
    i += 1
    ret = ""
    while i < len(s) and s[i] != start:
        ch = s[i]
        i += 1
        if ch == "\\" and i < len(s):
            ch = s[i]
            i += 1
            if ch == "n":
                ret += "\n"
            elif ch == "t":
                ret += "\t"
            elif ch == "r":
                ret += "\r"
            else:
                ret += ch
        else:
            ret += ch
    return ret, i

class Watcher:
    def __init__(self):
        self.history = [time.time()]

    def countup(self):
        if len(self.history) == 60:
            diff = self.history.pop(0) + 62 - time.time()
            if diff > 0:
                time.sleep(diff)
        self.history.append(time.time())

def make_history(history):
    if history is None:
        return None
    ret = []
    role = ["user", "model"]
    for i, h in enumerate(history):
        ret.append({ "role": role[i % 2], "parts": h.strip() })
    return ret

watcher = Watcher()
init_history = None
init_prompts = None
model = None
convo = None
chat_count = -1

def init(history=None, prompts=None):
    global init_history, init_prompts
    init_history = make_history(history)
    init_prompts = prompts
    start()

def start():
    global model, convo, chat_count
    print("Starting model...", file=sys.stderr)
    model = genai.GenerativeModel(model_name="gemini-pro",
                                  generation_config=generation_config,
                                  safety_settings=safety_settings)
    if init_history:
        convo = model.start_chat(history=init_history)
    else:
        convo = model.start_chat()
    if init_prompts:
        for p in init_prompts:
            query(p)
    chat_count = 0
    watcher.countup()

def query(prompt, info=None, show=False, retry=True, check=None):
    global chat_count
    q = common.query()
    q.prompt = prompt.replace("\r\n", "\n").rstrip()
    if info:
        q.info = info.strip()
    if show:
        print()
        if info:
            print(info)
        for line in prompt.split("\n"):
            print(">", line)
    for i in range(10):
        try:
            chat_count += 1
            watcher.countup()
            convo.send_message(q.prompt)
            r = convo.last.text.rstrip()
            if check and (e := check(r)):
                raise(Exception(e))
            q.result = r
            if show:
                print()
                print(r)
            break
        except Exception as e:
            err = str(e).rstrip()
            if show:
                print()
                print(err)
            if ("500 An internal error has occurred." in err or
                "429 Resource has been exhausted" in err):
                print("Retrying...", file=sys.stderr)
                time.sleep(5 + 2 * i)
                start()
                continue
            q.error = err
            if m := re.search("text: ", err):
                r, _ = parse(err, m.end())
                r = r.rstrip()
                if not (check and (e := check(r))):
                    q.result = r
                    if show:
                        print()
                        print(r)
                    break
            if retry and chat_count != 1:
                q.retry = True
                if show:
                    print()
                print("Retrying...", file=sys.stderr)
                start()
            else:
                start()
                break
    return q
