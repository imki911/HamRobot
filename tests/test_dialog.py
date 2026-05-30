from hamrobot.config import DialogConfig
from hamrobot.dialog.manager import DialogManager


def test_requires_wake_word():
    mgr = DialogManager(DialogConfig(require_wake_word=True, wake_words=["机器人"]))
    assert not mgr.decide("你好").should_reply
    assert mgr.decide("机器人收到请回答").should_reply


def test_trim_reply():
    mgr = DialogManager(DialogConfig(max_reply_chars=5, require_wake_word=False))
    assert mgr.trim_reply("一二三四五六七") == "一二三四五。"
