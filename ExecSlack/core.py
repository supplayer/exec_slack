from requests import Session
from datetime import datetime, timedelta
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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


class Basic:
    def __init__(self, token):
        self._session = Web(token)

    def _cursor_list(self, url: str, params: dict, data_field: str):
        while params['cursor'] or params['cursor'] is None:
            data = self._session.post(url, params=params).json()
            for item in data.get(data_field, []):
                yield item
            params['cursor'] = data['response_metadata'].get("next_cursor", '')

    @classmethod
    def _check_status(cls, res):
        if res.get('error'):
            raise ValueError(res)
        else:
            logger.info(res)
            return res


class Apps(Basic):
    def __init__(self, token):
        super().__init__(token)

    def requests_list(self):
        url = 'https://slack.com/api/admin.apps.requests.list'
        params = dict(cursor=None, enterprise_id=None, limit=100, team_id=None)
        self._check_status(self._session.post(url, params=params).json())


class Conversations(Basic):
    def __init__(self, token):
        super().__init__(token)

    def list(self, exclude_archived=False, limit=100, team_id=None, types="public_channel") -> iter:
        url = 'https://slack.com/api/conversations.list'
        params = dict(cursor=None, exclude_archived=exclude_archived, limit=limit, team_id=team_id, types=types)
        for channel in self._cursor_list(url, params, 'channels'):
            yield self._check_status(channel)

    def history(self, channel_id, latest=None, oldest=0, limit=100, inclusive=True) -> iter:
        url = 'https://slack.com/api/conversations.history'
        params = dict(channel=channel_id, cursor=None, latest=latest, oldest=oldest, limit=limit, inclusive=inclusive)
        for history in self._cursor_list(url, params, 'messages'):
            yield self._check_status(history)


class Chat(Basic):
    def __init__(self, token, conversations: Conversations):
        super().__init__(token)
        self.__conversations = conversations

    def delete(self, channel_id, ts, as_user=True):
        url = 'https://slack.com/api/chat.delete'
        params = dict(channel=channel_id, ts=ts, as_user=as_user)
        return self._check_status(self._session.post(url, params=params).json())

    def clear(self, channel_id, **del_time_offset):
        del_time_offset = del_time_offset or {"days": 90}
        latest = datetime.now().timestamp() - timedelta(**del_time_offset).total_seconds()
        for i in self.__conversations.history(channel_id, latest=latest):
            self.delete(channel_id, i['ts'])


class Slack:
    def __init__(self, token):
        self.apps = Apps(token)
        self.conversations = Conversations(token)
        self.chat = Chat(token, self.conversations)
