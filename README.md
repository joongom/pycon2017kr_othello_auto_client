## Othello Auto Client
- PyConKR2017 발표 자료를 준비하던 중에 만들게된 Othello 게임 서버에 접속하는 auto client
- 가장 기본적인 골격으로 구성하고 random 하게 놓을 곳을 선택
- 4개의 모서리는 무조건 먹는 로직이 추가

## 실행 방법
```
$ pip install protobuf
$ python test_client.py [user_uuid] [user_name]
```
- 참고로 user_uuid 로 별도 password 없이 로그인 되는 방식이므로 잘 정해서 입력해야 함
- user_name 은 unique 해야 하므로 잘 선택해서 입력해야 함

## 전략 코드 작성하는 곳
- Dispatcher class 의 GamePut 함수를 수정하여 전략이나 간단한 bot 을 구현할 수 있음

## 그 외 플레이가 실제 가능한 클라이언트
- PlayStore 에서 `오셀로 PyCon` 으로 검색하면 설치 가능
- [PlayStore Link](https://play.google.com/store/apps/details?id=kr.co.nnngomstudio.othello.googlemarket)

