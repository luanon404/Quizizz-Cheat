import json
import time
import uuid
from typing import Optional

import random
import requests
import websocket


class Quizizz:

    def __init__(self) -> None:
        self.session = requests.Session()
        self.headers = {
            "Host": "quizizz.com",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/117.0",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache"
        }

    def getTimeStamp(self) -> str:
        return str(int(time.time() * 1000))

    def getToken(self) -> str:
        url = "https://quizizz.com/join"
        self.session.get(url, headers=self.headers)
        return self.session.cookies.get("x-csrf-token")
    
    def getSocketSessionId(self) -> str:
        url = "https://socket.quizizz.com/_gsocket/sockUpg/?experiment=authRevamp&EIO=4&transport=polling"
        headers = {**self.headers, **{
            "Host": "socket.quizizz.com",
            "Referer": "https://quizizz.com/",
            "Origin": "https://quizizz.com",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site"
        }}
        resp = self.session.get(url, headers=headers)
        raw_data = resp.text
        while raw_data[0].isdigit():
            raw_data = raw_data[1:]
        data = json.loads(raw_data)
        sid = data["sid"]
        return sid
    
    def getRoomData(self, username: str, room_hash: str, sid: str) -> Optional[dict]:
        url = f"wss://socket.quizizz.com/_gsocket/sockUpg/?experiment=authRevamp&EIO=4&transport=websocket&sid={sid}"
        headers = {**self.headers, **{
            "Host": "socket.quizizz.com",
            "Origin": "https://quizizz.com",
            "Sec-WebSocket-Version": "13",
            "Sec-WebSocket-Extensions": "permessage-deflate",
            "Sec-WebSocket-Key": "VL1EbF+6fQLouGmzuRZz4g==",
            "Connection": "keep-alive, Upgrade",
            "Sec-Fetch-Dest": "websocket",
            "Sec-Fetch-Mode": "websocket",
            "Sec-Fetch-Site": "same-site",
            "Cookie": "; ".join([f"{k}={v}" for k, v in self.session.cookies.items()]),
            "Upgrade": "websocket"
        }}
        ws = websocket.WebSocket()
        ws.connect(url, header=headers)
        ws.send("2probe")
        while True:
            recv = ws.recv()
            if recv == "3probe":
                ws.send("5")
                register_data = "420" + json.dumps(["v5/join", {
                    "roomHash": room_hash,
                    "player": {
                        "id": username,
                        "origin": "web",
                        "isGoogleAuth": False,
                        "avatarId": 24,
                        "startSource": "gameCode.typed",
                        "userAgent": self.headers["User-Agent"],
                        "uid": str(uuid.uuid4()),
                        "expName": "peekabooAndPrac2_exp",
                        "expSlot": "100" # Default
                    },
                    "powerupInternalVersion": "20",
                    "__cid__": f"v5/join.|1.{self.getTimeStamp()}"
                }])
                ws.send(register_data)
            if recv.startswith("430"):
                if "OK" not in recv:
                    return None
                raw_data = ws.recv()
                while raw_data[0].isdigit():
                    raw_data = raw_data[1:]
                data = json.loads(raw_data)[1]
                ws.close()
                return data

    def getRightAnswer(self, game_id: str) -> Optional[dict]:
        result = {}
        url = f"https://quizizz.com/_api/main/game/{game_id}?_={self.getTimeStamp()}"
        headers = {**self.headers, **{
            "Accept": "application/json, text/plain, */*",
            "Referer": f"https://quizizz.com/admin/quiz/{game_id}/startV4?fromBrowserLoad=true&view=summary&didInitPractice=false",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "no-cors",
            "Sec-Fetch-Site": "same-origin"
        }}
        resp = self.session.get(url, headers=headers)
        data = resp.json()
        if data["success"]:
            for question in resp.json()["data"]["questions"]:
                result[question["_id"]] = question["structure"]["answer"]
        return result

    def checkRoom(self, join_code: str, token: str) -> Optional[str]:
        url = "https://game.quizizz.com/play-api/v5/checkRoom"
        data = json.dumps({"roomCode": join_code})
        headers = {**self.headers, **{
            "Host": "game.quizizz.com",
            "Accept": "application/json",
            "Referer": "https://quizizz.com/",
            "Content-Type": "application/json",
            "experiment-name": "peekabooAndPrac2_exp",
            "X-CSRF-TOKEN": token,
            "Content-Length": str(len(data)),
            "Origin": "https://quizizz.com",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site"
        }}
        resp = self.session.post(url, data, headers=headers)
        data = resp.json()
        if "room" in data:
            return data["room"]["hash"]

    def checkSocket(self, sid: str) -> bool:
        url = f"https://socket.quizizz.com/_gsocket/sockUpg/?experiment=authRevamp&EIO=4&transport=polling&sid={sid}"
        data = "40"
        headers = {**self.headers, **{
            "Host": "socket.quizizz.com",
            "Referer": "https://quizizz.com/",
            "Origin": "https://quizizz.com",
            "Content-Length": "2",
            "Content-Type": "text/plain;charset=UTF-8",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site"
        }}
        resp = self.session.post(url, data, headers=headers)
        raw_data = resp.text
        return raw_data == "ok"

    def postAnswer(self, username: str, room_hash: str, token: str, question_id: str, question_answer: str, room_version_id: str) -> dict:
        url = "https://game.quizizz.com/play-api/v4/proceedGame"
        data = json.dumps({
            "roomHash": room_hash,
            "playerId": username,
            "response": {
                "attempt": 0,
                "questionId": question_id,
                "questionType": "MCQ",
                "response": question_answer,
                "responseType": "original",
                "timeTaken": 50,
                "answer": [],
                "isEvaluated": False,
                "state": "attempted",
                "provisional": {
                    "scores": {
                        "correct": 5800,
                        "incorrect": 5000
                    },
                    "scoreBreakups": {
                        "correct": {
                            "base": 800,
                            "timer": 0,
                            "streak": 0,
                            "total": 5800,
                            "powerups": [{
                                "powerupEffectId": "639a0730e1b68c002275606d",
                                "powerupId": "639a071ed0b485001db2338b",
                                "name": "2x",
                                "score": 5000
                            }]
                        },
                        "incorrect": {
                            "base": 0,
                            "timer": 0,
                            "streak": 0,
                            "total": 5000,
                            "powerups": [{
                                "powerupEffectId": "639a0730e1b68c002275606d",
                                "powerupId": "639a071ed0b485001db2338b",
                                "name": "2x",
                                "score": 5000
                            }]
                        }
                    },
                    "teamAdjustments": {
                        "correct": 0,
                        "incorrect": 0
                    }
                }
            },
            "questionId": question_id,
            "powerupEffects": {
                "destroy": []
            },
            "gameType": "live",
            "quizVersionId": room_version_id
        })
        headers = {**self.headers, **{
            "Host": "game.quizizz.com",
            "Accept": "application/json",
            "Referer": "https://quizizz.com/",
            "Content-Type": "application/json",
            "experiment-name": "main_main",
            "X-CSRF-TOKEN": token,
            "Content-Length": str(len(data)),
            "Origin": "https://quizizz.com",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site"
        }}
        resp = self.session.post(url, data, headers=headers)
        data = resp.json()
        return data


if __name__ == "__main__":
    print("5800 points / correct question")
    print("5000 points / wrong question")
    print("="*30)
    print("Input join code")
    join_code = input(">>> ")
    print("Input your username")
    username = input(">>> ")
    print("Input delay per question (second)")
    delay = input(">>> ")
    quizizz = Quizizz()
    token = quizizz.getToken()
    room_hash = quizizz.checkRoom(join_code, token)
    if room_hash is None:
        print("Wrong join code!")
        exit()
    sid = quizizz.getSocketSessionId()
    if not quizizz.checkSocket(sid):
        print("Failed to join room!")
        exit()
    room_data = quizizz.getRoomData(username, room_hash, sid)
    if room_data is None:
        print("Failed to get room data!")
        exit()
    room_version_id = room_data["room"]["versionId"]
    questions = room_data["room"]["questions"]
    answers = quizizz.getRightAnswer(room_hash)
    random_choice = None
    if not answers:
        print("Can't get an answer. Would you like to choose randomly?")
        print("Enter 'Y' for Yes or any other key for No (default is Yes)")
        user_input = input(">>> ").strip().lower()
        if user_input and user_input != "y":
            random_choice = False
        else:
            random_choice = True
    input("Press Enter to start answering...")
    correct_question = 0
    wrong_question = 0
    total_point = 0
    for index, question_id in enumerate(questions.keys()):
        if random_choice:
            question_answer = random.randint(0, 3)
        else:
            question_answer = answers.get(question_id, 0)
        point = quizizz.postAnswer(username, room_hash, token, question_id, question_answer, room_version_id)["response"]["scoreBreakup"]["total"]
        total_point += point
        result = "Unknown"
        if point == 5800:
            correct_question += 1
            result = "CORRECT"
        elif point == 5000:
            wrong_question += 1
            result = "WRONG"
        else:
            print("Something wrong!!")
            print(f"DEBUG - {point}")
        print(f"Question {index + 1}, status _{result}_, point _{point}_, total point _{total_point}_")
        time.sleep(int(delay))
    print("Done!")
    print(f"Correct question: {correct_question}")
    print(f"Wrong question: {wrong_question}")
    print(f"Total point: {total_point}")
    print("Please give me star on Github if u like this <3")
