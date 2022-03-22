from requests import Session
from datetime import datetime, timedelta


class Web:
    def __init__(self, token):
        self.__data = {"token": token}
        self.__session = Session()
        self.__session.headers.update({
            "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/90.0.4430.212 Safari/537.36"})

    def post(self, url, params, data=None):
        return self.__session.post(url, params=params, data=data or self.__data)

    def get(self, url, params, data=None):
        return self.__session.get(url, params=params, data=data or self.__data)


class Conversations:
    def __init__(self, app_session: Web):
        self.__session = app_session

    def list(self, exclude_archived=False, limit=100, team_id=None, types="public_channel"):
        url, channel_list = 'https://slack.com/api/conversations.list', []
        params = dict(cursor=None, exclude_archived=exclude_archived, limit=limit, team_id=team_id, types=types)
        self.__cursor_list(url, params, channel_list, 'channels')
        return channel_list

    def history(self, channel_id, latest=None, oldest=0, limit=100, inclusive=True):
        url, history_list = 'https://slack.com/api/conversations.history', []
        params = dict(channel=channel_id, cursor=None, latest=latest, oldest=oldest, limit=limit, inclusive=inclusive)
        self.__cursor_list(url, params, history_list, 'messages')
        return history_list

    def __cursor_list(self, url: str, params: dict, record_list: list, data_field: str):
        while params['cursor'] or params['cursor'] is None:
            data = self.__session.post(url, params=params).json()
            record_list += [history for history in data[data_field]]
            params['cursor'] = data['response_metadata'].get("next_cursor", '')


class Chat:
    def __init__(self, app_session: Web, conversations: Conversations):
        self.__session = app_session
        self.__conversations = conversations

    def delete(self, channel_id, ts):
        url = 'https://slack.com/api/chat.delete'
        params = dict(channel=channel_id, ts=ts)
        return self.__session.post(url, params=params).json()

    def clear(self, channel_id, **del_time_offset):
        del_time_offset = del_time_offset or {"days": 90}
        latest = datetime.now().timestamp() - timedelta(**del_time_offset).total_seconds()
        return [self.delete(channel_id, i['ts']) for i in self.__conversations.history(channel_id, latest=latest)]


class Slack:
    def __init__(self, token):
        self.conversations = Conversations(Web(token))
        self.chat = Chat(Web(token), self.conversations)
