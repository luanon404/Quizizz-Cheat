import json
import time
import uuid
from typing import Optional

import requests
import websocket


class Quizizz:

    def __init__(self, power_up_slot: int = 100) -> None:
        self.power_up_slot = power_up_slot
        self.session = requests.Session()
        self.headers = {
            "Host": "quizizz.com",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:107.0) Gecko/20100101 Firefox/107.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache"
        }

    @staticmethod
    def get_timestamp() -> str:
        return str(int(time.time() * 1000))

    def get_x_csrf_token(self) -> str:
        url = "https://quizizz.com/join"
        self.session.get(url, headers=self.headers)
        return self.session.cookies.get("x-csrf-token")

    def check_room(self, join_code: str, x_csrf_token: str) -> Optional[str]:
        url = "https://game.quizizz.com/play-api/v5/checkRoom"
        data = json.dumps({"roomCode": join_code})
        headers = {**self.headers, **{
            "Host": "game.quizizz.com",
            "Accept": "application/json",
            "Referer": "https://quizizz.com/",
            "Content-Type": "application/json",
            "experiment-name": "peekabooAndPrac2_exp",
            "X-CSRF-TOKEN": x_csrf_token,
            "Content-Length": str(len(data)),
            "Origin": "https://quizizz.com",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site"
        }}
        resp = self.session.post(url, data, headers=headers).json()
        if resp.get("room", None):
            return resp["room"]["hash"]
        return None

    def get_socket_sid(self) -> str:
        url = "https://socket.quizizz.com/_gsocket/sockUpg/?experiment=authRevamp&EIO=4&transport=polling"
        headers = {**self.headers, **{
            "Host": "socket.quizizz.com",
            "Accept": "*/*",
            "Referer": "https://quizizz.com/",
            "Origin": "https://quizizz.com",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site"
        }}
        resp = self.session.get(url, headers=headers).text
        while resp[0].isdigit():
            resp = resp[1:]
        resp = json.loads(resp)
        return resp["sid"]

    def check_socket(self, sid: str) -> bool:
        url = f"https://socket.quizizz.com/_gsocket/sockUpg/?experiment=authRevamp&EIO=4&transport=polling&sid={sid}"
        data = "40"
        headers = {**self.headers, **{
            "Host": "socket.quizizz.com",
            "Accept": "*/*",
            "Referer": "https://quizizz.com/",
            "Origin": "https://quizizz.com",
            "Content-Length": "2",
            "Content-Type": "text/plain;charset=UTF-8",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site"
        }}
        resp = self.session.post(url, data, headers=headers).text
        if resp != "ok":
            return False
        return True

    def get_room_data(self, username: str, room_hash: str, sid: str) -> Optional[dict]:
        url = f"wss://socket.quizizz.com/_gsocket/sockUpg/?experiment=authRevamp&EIO=4&transport=websocket&sid={sid}"
        headers = {**self.headers, **{
            "Host": "socket.quizizz.com",
            "Accept": "*/*",
            "Origin": "https://quizizz.com",
            "Sec-WebSocket-Version": "13",
            "Sec-WebSocket-Extensions": "permessage-deflate",
            "Sec-WebSocket-Key": "VL1EbF+6fQLouGmzuRZz4g==",
            "Connection": "keep-alive, Upgrade",
            "Sec-Fetch-Dest": "websocket",
            "Sec-Fetch-Mode": "websocket",
            "Sec-Fetch-Site": "same-site",
            "Cookie": "; ".join([f"{x}={y}" for x, y in self.session.cookies.items()]),
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
                        "expSlot": str(self.power_up_slot)
                    },
                    "powerupInternalVersion": "20",
                    "__cid__": f"v5/join.|1.{self.get_timestamp()}"
                }])
                ws.send(register_data)
            if recv.startswith("430"):
                if "OK" not in recv:
                    return None
                resp = ws.recv()
                while resp[0].isdigit():
                    resp = resp[1:]
                resp = json.loads(resp)[1]
                ws.close()
                return resp

    def get_right_answer(self, game_id: str):
        url = f"https://quizizz.com/_api/main/game/{game_id}?_={self.get_timestamp()}"
        headers = {**self.headers, **{
            "Accept": "application/json, text/plain, */*",
            "Referer": f"https://quizizz.com/admin/quiz/{game_id}/startV4?fromBrowserLoad=true&view=summary&didInitPractice=false",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "no-cors",
            "Sec-Fetch-Site": "same-origin"
        }}
        resp = self.session.get(url, headers=headers)
        result = {}
        for question in resp.json()["data"]["questions"]:
            result[question["_id"]] = question["structure"]["answer"]
        return result

    def post_answer(self, username: str, room_hash: str, x_csrf_token: str, question_id: str, question_answer: str, room_version_id: str) -> dict:
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
            "X-CSRF-TOKEN": x_csrf_token,
            "Content-Length": str(len(data)),
            "Origin": "https://quizizz.com",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site"
        }}
        resp = self.session.post(url, data, headers=headers)
        return resp.json()


if __name__ == "__main__":
    print("Input join code")
    join_code = input(">>> ")
    print("Input your username")
    username = input(">>> ")
    print("Input delay per question")
    delay = input(">>> ")
    quizizz = Quizizz()
    x_csrf_token = quizizz.get_x_csrf_token()
    room_hash = quizizz.check_room(join_code, x_csrf_token)
    if room_hash is None:
        print("Wrong join code!")
        exit()
    sid = quizizz.get_socket_sid()
    if not quizizz.check_socket(sid):
        print("Fail to join room!")
        exit()
    room_data = quizizz.get_room_data(username, room_hash, sid)
    if room_data is None:
        print("Fail to register socket!")
        exit()
    room_version_id = room_data["room"]["versionId"]
    questions = room_data["room"]["questions"]
    answers = quizizz.get_right_answer(room_hash)
    input("Press Enter to answer...")
    for index, question_id in enumerate(questions.keys()):
        print(f"{index + 1}-{quizizz.post_answer(username, room_hash, x_csrf_token, question_id, answers[question_id], room_version_id)['response']['scoreBreakup']['total']}")
        time.sleep(int(delay))
    print("Done!")
