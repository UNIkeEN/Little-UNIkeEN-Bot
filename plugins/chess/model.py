from datetime import datetime
from utils.sqlUtils import newSqlSession
raise NotImplementedError
class GameRecord():
    @staticmethod
    def createSql():
        mydb, mycursor = newSqlSession()
        mycursor.execute("""
        create table if not exists `chessGameRecord`(
            `group_id` big int unsigned not null,
            `start_time` timestamp default null,
            primary key (`group_id`)
        )
        """)
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[str] = mapped_column(String(128))
    session_id: Mapped[str] = mapped_column(String(128))
    start_time: Mapped[datetime] = mapped_column(default=datetime.now())
    """ 游戏开始时间 """
    update_time: Mapped[datetime] = mapped_column(default=datetime.now())
    """ 游戏更新时间 """
    player_white_id: Mapped[str] = mapped_column(String(64), default="")
    """ 白方id """
    player_white_name: Mapped[str] = mapped_column(Text, default="")
    """ 白方名字 """
    player_black_id: Mapped[str] = mapped_column(String(64), default="")
    """ 黑方id """
    player_black_name: Mapped[str] = mapped_column(Text, default="")
    """ 黑方名字 """
    start_fen: Mapped[str] = mapped_column(Text, default="")
    """ 起始局面FEN字符串 """
    moves: Mapped[str] = mapped_column(Text, default="")
    """ 所有移动，uci形式，以空格分隔 """
    is_game_over: Mapped[bool] = mapped_column(default=False)
    """ 游戏是否已结束 """
