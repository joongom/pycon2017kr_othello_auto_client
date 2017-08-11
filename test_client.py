import sys
import random
import time
import othello_pb2
import requests
import uuid

req_protocol_map = {}
for field in othello_pb2._REQUEST.fields:
    if field.message_type is not None :
        req_protocol_map[field.message_type.name] = [field.name, field.number]

rsp_protocol_map = {}
for field in othello_pb2._RESPONSE.fields:
    if field.message_type is not None :
        rsp_protocol_map[field.number] = [field.name, field.message_type.name]

client = None

class Dispatcher:
    dir_k = [[0, -1], [-1, -1], [-1, 0], [-1, 1], [0, 1], [1, 1], [1, 0], [1, -1]]
    special_k = [[0, 0], [7, 0], [0, 7], [7, 7]]

    def __init__(self):
        pass

    def CheckBoard(self, board_data, r, c, ubi, obi):
        if board_data[r * 8 + c] != othello_pb2.Empty:
            return False

        for k in range(8):
            for j in range(1, 8):

                r2 = self.dir_k[k][0] * j + r
                c2 = self.dir_k[k][1] * j + c
                if r2 < 0 or r2 > 7 or c2 < 0 or c2 > 7:
                    break

                i2 = r2 * 8 + c2
                if board_data[i2] == obi:
                    continue
                if board_data[i2] == ubi and j > 1:
                    return True
                break
        return False

    def GetPositionList(self, board_data, ubi):
        obi = othello_pb2.Black if ubi == othello_pb2.White else othello_pb2.White

        ret = []
        for r in range(8):
            for c in range(8):
                if self.CheckBoard(board_data, r, c, ubi, obi):
                    ret.append([r, c])
        return ret

    def GamePut(self, ubi):
        # Put 로직
        positions = self.GetPositionList(client.room.board, ubi)
        for p in self.special_k:
            if p in positions:
                client.rpc(othello_pb2.ReqGamePut(room_id=client.room.room_id, r=p[0], c=p[1]))
                return

        r, c = positions[random.randint(0, len(positions) - 1)]
        client.rpc(othello_pb2.ReqGamePut(room_id=client.room.room_id, r=r, c=c))

    def RspLogin(self, result, rsp):
        if result.code == othello_pb2.ErrorUserNotRegistered:
            client.rpc(othello_pb2.ReqRegister(
                platform_type=othello_pb2.CUSTOM,
                platform_token=client.user_platform_token,
                name=client.user_name
            ))
        elif result.code == othello_pb2.Success:
            client.user = rsp.user
            client.token = rsp.token

            # client.rpc(othello_pb2.ReqCreateGameRoom())
            client.rpc(othello_pb2.ReqRandomJoin())

    def RspRegister(self, result, rsp):
        if result.code == othello_pb2.Success:
            client.rpc(othello_pb2.ReqLogin(
                platform_type=othello_pb2.CUSTOM,
                platform_token=client.user_platform_token
            ))
        else:
            raise Exception(str(result.code))

    def RspJoinGameRoom(self, result, rsp):
        if result.code == othello_pb2.Success:
            client.room = rsp.room
            client.opponent = rsp.opponent

            time.sleep(3)
            client.rpc(othello_pb2.ReqGameSync(room_id=client.room.room_id))
        # room_id 로 직접 조인하는 경우는 없으므로 오류 상황은 없음

    def RspRandomJoin(self, result, rsp):
        if result.code == othello_pb2.ErrorInvalidGameRoom:
            client.rpc(othello_pb2.ReqCreateGameRoom())
        # 그외에 성공한 경우는 JoinGameRoom 이 실행

    def RspCreateGameRoom(self, result, rsp):
        if result.code == othello_pb2.Success:
            client.room = rsp.room

            time.sleep(3)
            client.rpc(othello_pb2.ReqGameSync(room_id=client.room.room_id))
        # create 실패는 무언가 서버에 큰 문제가 있는 경우이므로 추가 요청 없이 종료하도록 유도

    def RspExitGameRoom(self, result, rsp):
        # 게임 클라이언트가 직접 종료하는 rpc 실행은 하지 않음
        pass

    def RspGamePut(self, result, rsp):
        pass

    def PrintBoard(self):
        board_to_char = {othello_pb2.White: 'O', othello_pb2.Black: 'X', othello_pb2.Empty: '.'}
        score_o = 0
        score_x = 0
        print('+--------+')
        for r in range(0, 8):
            print('|', end='')
            for c in range(0, 8):
                bc = board_to_char[client.room.board[r * 8 + c]]
                print(bc, end='')
                if bc == 'O': score_o += 1
                if bc == 'X': score_x += 1
            print('|')
        print('+--------+')
        print('O Score : {}, X Score : {}'.format(score_o, score_x))

    def RspGameSync(self, result, rsp):
        if result.code == othello_pb2.Success:
            # game sync 결과로 내 턴인경우 put 진행
            client.room = rsp.room
            self.PrintBoard()
            if (client.room.status == othello_pb2.GameRoom.TURN_USER1 and \
                            client.room.user_1 == client.user.id):
                self.GamePut(othello_pb2.White)
            elif (client.room.status == othello_pb2.GameRoom.TURN_USER2 and \
                            client.room.user_2 == client.user.id):
                self.GamePut(othello_pb2.Black)
            elif client.room.status not in [othello_pb2.GameRoom.GAME_OVER, othello_pb2.GameRoom.TIMEOUT]:
                time.sleep(3)
                client.rpc(othello_pb2.ReqGameSync(room_id=client.room.room_id))

    def RspGameOver(self, result, rsp):
        client.user = rsp.user
        if rsp.winner == client.user.id:
            print('YOU WIN')
        elif rsp.winner != 0:
            print('YOU LOSE')
        else:
            print('DRAW')
        print(client.user)
        time.sleep(3)
        client.rpc(othello_pb2.ReqRandomJoin())
        # client.rpc(othello_pb2.ReqCreateGameRoom())


class OthelloClient:
    dispatcher = None
    server_url = None
    user_platform_token = None
    user_name = None
    rpc_queue = None
    room = None
    user = None
    token = None

    def __init__(self, url, user_platform_token, user_name, dispatcher):
        self.server_url = url
        self.user_platform_token = user_platform_token
        self.user_name = user_name
        self.dispatcher = dispatcher
        self.rpc_queue = []

    def __rpc(self, remote_procedure):
        print('client --> server rpc : {}'.format(remote_procedure.DESCRIPTOR.name))
        req = othello_pb2.Request(protocolVersion=othello_pb2.V_LATEST)

        if remote_procedure.DESCRIPTOR.name in req_protocol_map:
            name, tag = req_protocol_map[remote_procedure.DESCRIPTOR.name]
            req.protocolVersion = int(othello_pb2.V_LATEST)
            req.protocolId = tag
            if self.token is not None:
                req.token = self.token

            getattr(req, name).CopyFrom(remote_procedure)

        http_rsp = requests.post(self.server_url, data=req.SerializeToString(),
                                 timeout=5, headers={})
        if http_rsp.status_code == 200:
            rsp = othello_pb2.MultipleResponse.FromString(http_rsp.content)

            for rsp in rsp.responses:
                field_name, procedure_name = rsp_protocol_map[rsp.protocolId]
                print(' server --> client rpc : {}, result_code({})'.format(
                    procedure_name, othello_pb2.ResultCode.Name(rsp.result.code)))

                if rsp.HasField(field_name):
                    rpc_return = getattr(rsp, field_name)
                else:
                    continue

                p = getattr(self.dispatcher, procedure_name)
                if p is not None:
                    p(rsp.result, rpc_return)

        return http_rsp.status_code

    def rpc(self, remote_procedure):
        if remote_procedure.DESCRIPTOR.name == 'ReqGameSync':
            for rp in self.rpc_queue:
                if rp.DESCRIPTOR.name == 'ReqGameSync':
                    # 2중으로 요청하지 않는다
                    return
        self.rpc_queue.append(remote_procedure)

    def run(self):
        self.rpc(othello_pb2.ReqLogin(platform_type=othello_pb2.CUSTOM,
                                   platform_token=self.user_platform_token))
        while len(self.rpc_queue) > 0:
            remote_procedure = self.rpc_queue.pop(0)
            status_code = self.__rpc(remote_procedure)
            # print('status_code:{}'.format(status_code))
            if status_code != 200:
                self.rpc_queue.insert(0, remote_procedure)
                time.sleep(5)

if __name__ == '__main__' and len(sys.argv) == 3:
    client = OthelloClient(url='http://ecs-othello-1313342875.ap-northeast-1.elb.amazonaws.com:14500/api',
                           user_platform_token=sys.argv[1],
                           user_name=sys.argv[2], dispatcher=Dispatcher())
    client.run()

